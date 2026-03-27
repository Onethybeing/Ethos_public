import os
import json
from typing import List, Literal
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from groq import Groq
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# Configuration & Initialization
# ---------------------------------------------------------
# Load environment variables (reusing the factchecker .env where Qdrant credentials live)
load_dotenv(r"C:\Users\soura\ethos\Ethos\backend\.env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "news_articles_streaming"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # MUST be added to your .env file

# Choose a speedy, lightweight Llama 3 model available on Groq
GROQ_MODEL = "llama-3.1-8b-instant" 

# ---------------------------------------------------------
# Step 1: Strict Pydantic Data Models (Structured Output)
# ---------------------------------------------------------
class ClaimList(BaseModel):
    claims: List[str] = Field(description="A list of atomic factual claims extracted from the text.")

class ClaimEvaluation(BaseModel):
    claim: str = Field(description="The atomic claim being evaluated.")
    classification: Literal["Supported", "Contradicted", "Not Mentioned"] = Field(
        description="Must be 'Supported', 'Contradicted', or 'Not Mentioned'."
    )
    explanation: str = Field(description="Brief explanation of the reasoning based strictly on the provided evidence.")
    supporting_urls: List[str] = Field(description="List of exact URLs from the evidence that support the conclusion.", default=[])

class FinalFactCheckResult(BaseModel):
    evaluations: List[ClaimEvaluation]

# ---------------------------------------------------------
# Fact-Checking Engine 
# ---------------------------------------------------------
class FactChecker:
    def __init__(self):
        print("Initializing Fact Checker...")
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing! Please add it to C:\\Users\\soura\\ethos\\factchecker\\.env")
            
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

    def _get_json_response(self, system_prompt: str, user_prompt: str, json_schema: dict) -> dict:
        """Helper to force Groq LLM to return strictly formatted Pydantic-compliant JSON."""
        # Groq supports native JSON schema formatting on certain models or standard prompt enforcement
        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\nYou MUST return raw JSON that precisely matches this JSON schema:\n{json.dumps(json_schema, indent=2)}\n\nDo not return markdown blocks, only raw parsable JSON."
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
        
        response = self.groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0  # Zero hallucination strictly parsing
        )
        return json.loads(response.choices[0].message.content)

    def extract_claims(self, text: str) -> List[str]:
        """Step 1: Break main article down into atomic factual claims."""
        print("\n=> [Step 1] Extracting claims from the text...")
        system_prompt = (
            "You are a meticulous fact-checking assistant. Your sole task is to break down the provided "
            "text into distinct, atomic factual claims. An atomic claim should represent one singular, "
            "verifiable fact without compound conjunctions (e.g., 'Company X announced Y' and 'Company X "
            "did this on Tuesday' should be separate claims).\n"
            "CRITICAL RULES FOR NUMBERS:\n"
            "- Pay special attention to exact numbers, dollar amounts, percentages, quantities, and dates.\n"
            "- Extract numerical or statistical statements into their own independent atomic claims (e.g. 'Telegram was fined $1 million' becomes 'Telegram was fined', 'The fine amount was $1 million').\n"
            "- Ignore opinions and rhetorical questions."
        )
        
        result_dict = self._get_json_response(
            system_prompt=system_prompt, 
            user_prompt=f"TEXT TO EXTRACT:\n{text}",
            json_schema=ClaimList.model_json_schema()
        )
        claims = result_dict.get("claims", [])
        for i, c in enumerate(claims, 1):
            print(f"   [{i}] {c}")
        return claims

    def retrieve_evidence(self, claim: str, limit: int = 4):
        """Step 2: Compare each claim against retrieved articles from Qdrant stream."""
        # print(f"   Gathering evidence for: '{claim}'")
        query_vector = self.encoder.encode(claim).tolist()
        
        raw_results = self.qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit
        )
        
        evidence_snippets = []
        for hit in raw_results:
            source = hit.payload.get('source', '')
            content = hit.payload.get('content', '')[:500] # Take first 500 chars for context
            evidence_snippets.append({"source_url": source, "content": content})
            
        return evidence_snippets

    def classify_claim(self, claim: str, evidence_list: list) -> ClaimEvaluation:
        """Step 3: Classify the claim based strictly on the retrieved context."""
        system_prompt = (
            "You are an impartial, strict Fact-Checking Judge. Your goal is to evaluate the CLAIM "
            "using ONLY the PROVIDED EVIDENCE.\n"
            "Rules:\n"
            "1. Output exactly matching the required JSON schema.\n"
            "2. If the evidence directly validates the claim, label it 'Supported'.\n"
            "3. If the evidence directly contradicts the claim, label it 'Contradicted'.\n"
            "4. If the evidence does not provide enough information to prove or disprove the claim, "
            "label it 'Not Mentioned'. DO NOT use outside knowledge.\n"
            "5. FOCUS ON NUMBERS: If the claim contains specific numbers (e.g., $2 million, 50%, specific dates) and the evidence explicitly states a DIFFERENT number (e.g., $1 million), you MUST label it 'Contradicted'.\n"
            "6. SOURCES: If your label is 'Supported' or 'Contradicted', you MUST extract and include the exact 'source_url' from the matched evidence in the `supporting_urls` list. If 'Not Mentioned', leave the list empty."
        )
        
        evidence_text = json.dumps(evidence_list, indent=2)
        user_prompt = f"CLAIM: {claim}\n\nPROVIDED EVIDENCE:\n{evidence_text}"

        result_dict = self._get_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=ClaimEvaluation.model_json_schema()
        )
        return ClaimEvaluation(**result_dict)

    def run_full_pipeline(self, input_text: str):
        print("\n" + "="*50)
        print("  STARTING FACT-CHECKING PIPELINE")
        print("="*50)
        
        # 1. Extract
        claims = self.extract_claims(input_text)
        
        # 2 & 3. Retrieve and Evaluate
        evaluations = []
        print("\n=> [Step 2 & 3] Cross-referencing Qdrant and classifying...")
        for claim in claims:
            evidence = self.retrieve_evidence(claim)
            evaluation = self.classify_claim(claim, evidence)
            evaluations.append(evaluation)
            
            # Print Live Results neatly
            print(f"\n[-] CLAIM: {evaluation.claim}")
            print(f"    LABEL: [{evaluation.classification.upper()}]")
            print(f"    REASON: {evaluation.explanation}")
            if evaluation.supporting_urls:
                print(f"    SOURCES: {', '.join(evaluation.supporting_urls)}")
                
        # Return final strict Pydantic Output Document
        final_result = FinalFactCheckResult(evaluations=evaluations)
        return final_result


if __name__ == "__main__":
    # --- Example Usage --- #
    engine = FactChecker()
    
    sample_article_to_check = (
        "In a surprising turn of events, President Trump recently issued a new Executive Order "
        "expanding the powers of independent agencies, specifically placing higher budgets in the FCC. "
        "Meanwhile, Telegram was fined $1 million by the Australian eSafety commissioner."
    )
    
    # Needs GROQ_API_KEY in C:\\Users\\soura\\ethos\\factchecker\\.env to run!
    try:
        final_json_data = engine.run_full_pipeline(sample_article_to_check)
        
        # Save output to a JSON file in the same directory
        output_file_path = os.path.join(os.path.dirname(__file__), "fact_check_results.json")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(final_json_data.model_dump_json(indent=2))
        
        print(f"\n\n==== SUCCESSFULLY SAVED STRICT JSON OUTPUT TO: {output_file_path} ====")
        # Uncomment below if you also want to print it to the terminal
        # print(final_json_data.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"\nPipeline Error: {e}")
        print("\nMake sure you have: pip install groq pydantic")
        print("And that you added GROQ_API_KEY=gsk_... to your .env file!")