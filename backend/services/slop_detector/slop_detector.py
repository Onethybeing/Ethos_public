"""
AI Slop Detector Module.
Detects AI-generated news articles using local statistical and linguistic signals.
Relies entirely on standard Python libraries and a pre-loaded spaCy model.
"""

from collections import Counter
import math

class SlopDetector:
    """
    Detects potential AI-generated text using statistical distributions and 
    linguistic markers without relying on external ML models or APIs.
    """

    def __init__(self, nlp):
        """
        Initializes the SlopDetector.
        
        Args:
            nlp: A pre-loaded spaCy language model (e.g., en_core_web_sm).
        """
        self.nlp = nlp

    def _calculate_burstiness(self, sentence_lengths: list[int]) -> float:
        """
        Calculates burstiness based on the variance of sentence lengths.
        AI text often has low variance (highly consistent lengths).
        
        Args:
            sentence_lengths: List of lengths (in words) of each sentence.
            
        Returns:
            float: Burstiness score from 0.0 to 1.0 (1.0 = highly AI-like/low variance).
        """
        if len(sentence_lengths) < 2:
            return 0.0
            
        mean_length = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((x - mean_length) ** 2 for x in sentence_lengths) / len(sentence_lengths)
        std_dev = math.sqrt(variance)
        
        # Coefficient of variation (CV) represents burstiness. 
        # Human text typically has a CV > 0.4. AI text often has CV < 0.2.
        # We invert and normalize this so that a lower CV yields a higher AI score.
        cv = std_dev / mean_length if mean_length > 0 else 0
        
        # Map CV to 0-1 (cap at 0.5 for normalization). 
        # If CV is 0 (all sentences same length), score is 1.0. 
        # If CV >= 0.5 (highly variable), score is 0.0.
        ai_score = max(0.0, 1.0 - (cv / 0.5))
        return min(1.0, ai_score)

    def _calculate_repetition(self, words: list[str], n_gram_size: int = 4) -> float:
        """
        Calculates the ratio of repeated n-grams.
        AI text often contains high n-gram repetition.
        
        Args:
            words: List of words in the text.
            n_gram_size: The size of the word phrases to check for repetition.
            
        Returns:
            float: Repetition score from 0.0 to 1.0 (1.0 = highly repetitive).
        """
        if len(words) < n_gram_size:
            return 0.0
            
        n_grams = [
            tuple(words[i:i+n_gram_size]) 
            for i in range(len(words) - n_gram_size + 1)
        ]
        
        counts = Counter(n_grams)
        total_ngrams = len(n_grams)
        
        if total_ngrams == 0:
            return 0.0
            
        # Count n-grams that appear more than once
        repeated_ngrams = sum(count for count in counts.values() if count > 1)
        
        # Ratio of repeated n-grams to total n-grams
        ratio = repeated_ngrams / total_ngrams
        
        # Typically, a repetition ratio over 10% (0.1) in 4-grams is very high.
        # Normalize so that 0.1 ratio = 1.0 score.
        return min(1.0, ratio / 0.1)

    def _calculate_entity_density(self, doc) -> float:
        """
        Calculates named entity density per 100 words.
        AI text often hallucinates less or uses fewer concrete entities than human journalism.
        
        Args:
            doc: A processed spaCy Doc object.
            
        Returns:
            float: Entity density score from 0.0 to 1.0 (1.0 = low density/AI-like).
        """
        words = [token for token in doc if not token.is_punct and not token.is_space]
        word_count = len(words)
        
        if word_count == 0:
            return 0.0
            
        # Count specific factual entities
        target_labels = {"PERSON", "ORG", "GPE"}
        entity_count = sum(1 for ent in doc.ents if ent.label_ in target_labels)
        
        entities_per_100 = (entity_count / word_count) * 100
        
        # Human news typically has > 8 entities per 100 words.
        # AI often has < 3. We invert so fewer entities = closer to 1.0.
        if entities_per_100 >= 8.0:
            return 0.0
        return max(0.0, 1.0 - (entities_per_100 / 8.0))

    def _calculate_passive_voice(self, doc) -> float:
        """
        Calculates the ratio of sentences containing passive voice constructions.
        AI summarizations often default heavily to passive voice.
        
        Args:
            doc: A processed spaCy Doc object.
            
        Returns:
            float: Passive voice score from 0.0 to 1.0 (1.0 = high passive usage).
        """
        sentences = list(doc.sents)
        if not sentences:
            return 0.0
            
        passive_sentence_count = 0
        
        for sent in sentences:
            # Check for standard passive dependency tags (auxpass, nsubjpass)
            is_passive = any(token.dep_ in ("auxpass", "nsubjpass") for token in sent)
            if is_passive:
                passive_sentence_count += 1
                
        ratio = passive_sentence_count / len(sentences)
        
        # Normal human text might have ~15% passive sentences. If > 40%, highly AI-like.
        # Normalize so >= 40% (0.4) is 1.0.
        return min(1.0, ratio / 0.4)

    def _calculate_uniformity(self, sentence_lengths: list[int]) -> float:
        """
        Calculates how uniformly distributed the sentence lengths are.
        AI text strongly gravitates toward medium-length sentences, lacking very short
        or very long human-like variations.
        
        Args:
            sentence_lengths: List of lengths (in words) of each sentence.
            
        Returns:
            float: Uniformity score from 0.0 to 1.0 (1.0 = highly uniform).
        """
        if len(sentence_lengths) < 2:
            return 0.0
            
        # Check percentage of sentences that fall strictly between 12 and 25 words
        # (The quintessential AI "safe" sentence length)
        medium_sentences = sum(1 for x in sentence_lengths if 12 <= x <= 25)
        uniformity_ratio = medium_sentences / len(sentence_lengths)
        
        # If > 70% of sentences fall exactly in this band, it's highly uniform/AI.
        return min(1.0, uniformity_ratio / 0.70)

    def analyze(self, text: str, doc=None) -> dict:
        """
        Analyzes the text using local statistical signals to detect AI generation.
        
        Args:
            text: The news article text to analyze.
            
        Returns:
            dict: A dictionary containing the final score, label, and individual signal scores.
        """
        # Edge Cases
        if not text or not text.strip():
            return self._build_empty_response()

        if doc is None:
            doc = self.nlp(text)
        
        # Filter purely for actual words (ignore punctuation/whitespace)
        words = [token.text.lower() for token in doc if not token.is_punct and not token.is_space]
        word_count = len(words)
        
        # If text is too short, return insufficient content.
        if word_count < 150:
            return self._build_empty_response()

        # Compute Base Metrics
        sentences = list(doc.sents)
        sentence_lengths = [
            len([t for t in sent if not t.is_punct and not t.is_space]) 
            for sent in sentences
        ]

        # Calculate Individual Signals
        burstiness = self._calculate_burstiness(sentence_lengths)
        repetition = self._calculate_repetition(words, n_gram_size=4)
        entity_density = self._calculate_entity_density(doc)
        passive_voice = self._calculate_passive_voice(doc)
        uniformity = self._calculate_uniformity(sentence_lengths)

        # Calculate Final Weighted Score
        final_score = (
            (burstiness * 0.3) + 
            (repetition * 0.25) + 
            (entity_density * 0.2) + 
            (passive_voice * 0.15) + 
            (uniformity * 0.1)
        )

        # Determine Label based on rules
        if final_score < 0.35:
            label = "human"
        elif 0.35 <= final_score <= 0.65:
            label = "uncertain"
        else:
            label = "ai_generated"

        return {
            "ai_slop_score": round(final_score, 4),
            "ai_slop_label": label,
            "burstiness_score": round(burstiness, 4),
            "repetition_ratio": round(repetition, 4),
            "entity_density": round(entity_density, 4),
            "passive_voice_ratio": round(passive_voice, 4),
            "uniformity_score": round(uniformity, 4)
        }

    def _build_empty_response(self) -> dict:
        """Helper to return the default response for invalid/short edge cases."""
        return {
            "ai_slop_score": None,
            "ai_slop_label": "insufficient_content",
            "burstiness_score": 0.0,
            "repetition_ratio": 0.0,
            "entity_density": 0.0,
            "passive_voice_ratio": 0.0,
            "uniformity_score": 0.0
        }
