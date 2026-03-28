import { motion } from 'framer-motion'
import styles from './Button.module.css'

export default function Button({
  children,
  variant = 'primary',
  disabled = false,
  onClick,
  type = 'button',
  className = '',
}) {
  return (
    <motion.button
      type={type}
      className={`${styles.btn} ${styles[variant]} ${className}`}
      disabled={disabled}
      onClick={onClick}
      whileTap={disabled ? {} : { scale: 0.97 }}
      whileHover={disabled ? {} : { y: -1 }}
    >
      {children}
    </motion.button>
  )
}
