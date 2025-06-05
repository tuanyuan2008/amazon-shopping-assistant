# Default score when a required attribute is missing from a product
MISSING_SCORE = 0.15

# Maximum number of LLM validation calls per ranking run
# This was previously used by ProductScorer directly, but relevance validation is now a post-processing step.
# Keeping it for now in case the new post-processing step wants to use a similar counter,
# but it's distinct from TOP_N_FOR_LLM_VALIDATION which determines how many products to check.
MAX_LLM_VALIDATIONS_PER_RUN = 10

# Number of top products to validate with LLM in the post-processing step
TOP_N_FOR_LLM_VALIDATION = 25
