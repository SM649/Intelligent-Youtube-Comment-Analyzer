# In optimized_key_insights.py
from transformers import pipeline, AutoTokenizer
import logging
import torch
import os
import gc
from functools import lru_cache
import random # Added import for random selection

# Configure logging with less verbose output for production
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use environment variables to control transformers verbosity
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "true"  # Enable tokenizer parallelism

# Global variables for models to avoid reloading
global_tokenizer = None
global_summarizer = None

@lru_cache(maxsize=1024)
def cached_encode(text_segment):
    """Cache encoding results to avoid redundant tokenization of similar text."""
    global global_tokenizer
    return global_tokenizer.encode(text_segment, add_special_tokens=False)

def create_text_chunks(text, tokenizer, max_token_length, overlap):
    """Splits text into chunks based on token count with overlap - optimized version."""
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception as e:
            logging.error(f"Failed to convert input to string: {e}")
            return []

    try:
        # Tokenize in one go to avoid redundant processing
        tokens = tokenizer.encode(text, add_special_tokens=False)
        num_tokens = len(tokens)
    except Exception as e:
        logging.error(f"Error encoding text: {e}")
        return []

    chunks = []
    start = 0
    
    # Use more efficient chunking logic
    while start < num_tokens:
        end = min(start + max_token_length, num_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        
        if chunk_text.strip():
            chunks.append(chunk_text)
        
        # Advance pointer with overlap
        start += max_token_length - overlap
        
        # Safety check to prevent infinite loops
        if start >= num_tokens or (len(chunks) > 0 and start >= end):
            break

    return chunks

def initialize_models(model_name="facebook/bart-large-cnn"):
    """Initialize models once and store in global variables."""
    global global_tokenizer, global_summarizer
    
    # Only initialize if not already done
    if global_tokenizer is None:
        try:
            logging.info(f"Initializing tokenizer with '{model_name}'")
            global_tokenizer = AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            logging.error(f"Failed to initialize tokenizer: {e}")
            return False
    
    if global_summarizer is None:
        try:
            # Use smaller faster model instead of t5-base
            # Determine optimal device
            device = -1  # Default to CPU (-1)
            
            # Only use CUDA if there's enough GPU memory (>= 2GB free)
            if torch.cuda.is_available():
                try:
                    # Get free memory in MB
                    free_mem = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
                    free_mem_mb = free_mem / (1024 * 1024)
                    
                    if free_mem_mb >= 2000:  # If at least 2GB free
                        device = 0  # Use GPU
                        logging.info(f"Using GPU with {free_mem_mb:.2f}MB free memory")
                    else:
                        logging.info(f"Not enough GPU memory ({free_mem_mb:.2f}MB free). Using CPU.")
                except:
                    logging.info("Could not determine GPU memory. Defaulting to CPU.")
            
            # Initialize pipeline with optimized settings
            global_summarizer = pipeline(
                "summarization",
                model=model_name,
                tokenizer=global_tokenizer,
                framework="pt",
                device=device,
                batch_size=2  # Batch size adjusted for your hardware
            )
            logging.info(f"Summarization pipeline initialized with model '{model_name}'")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize summarizer: {e}")
            return False
    
    return True

def summarize_comments(text, final_max_length=100, final_min_length=10):
    """
    Optimized version of summarize_comments using a faster model and better processing.
    Selects a random subset of 5 chunks if more than 5 are generated.
    """
    # Use a smaller, faster model instead of t5-base
    model_name = "facebook/bart-large-cnn"  # Much faster than t5-base for summarization
    
    # Initialize models if not already done
    if not initialize_models(model_name):
        return ""
        
    # Access global variables
    global global_tokenizer, global_summarizer
    
    # Handle list input
    if isinstance(text, list):
        text = "\n".join(text)
    
    if not text or not text.strip():
        return ""
    
    # Get model's max input size - BART typically has 1024
    max_input_tokens = 1024
    try:
        max_input_tokens = global_tokenizer.model_max_length
        if max_input_tokens > 2048 or max_input_tokens <= 0:
            max_input_tokens = 1024  # Sane default for BART
    except:
        max_input_tokens = 1024
    
    # Set parameters for intermediate steps - adjusted for efficiency
    intermediate_max_length = min(int(max_input_tokens * 0.25), 150)  # Shorter summaries for speed
    intermediate_min_length = min(int(max_input_tokens * 0.05), 30)
    overlap = min(int(max_input_tokens * 0.08), 40)  # Smaller overlap for speed
    
    # Ensure sane parameter values
    intermediate_max_length = max(intermediate_max_length, intermediate_min_length + 5)
    overlap = min(overlap, int(max_input_tokens * 0.5))
    overlap = max(0, overlap)
    
    # Clean up memory before starting the process
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    
    # Main summarization loop
    current_text = text
    iteration = 0
    max_iterations = 3  # Limit iterations for speed
    
    while iteration < max_iterations:
        iteration += 1
        logging.info(f"Starting iteration {iteration}")
        
        try:
            # Count tokens
            tokens = global_tokenizer.encode(current_text, add_special_tokens=True)
            num_tokens = len(tokens)
            logging.info(f"Current text has {num_tokens} tokens")
            
            # If text is short enough, perform final summarization
            if num_tokens <= max_input_tokens:
                summary_result = global_summarizer(
                    current_text,
                    max_length=final_max_length,
                    min_length=final_min_length,
                    do_sample=False,
                    truncation=True
                )
                summary = summary_result[0]['summary_text']
                
                if not summary.strip() or summary.lower() == "summarize:":
                    return ""
                    
                return summary
            
            # Text is too long, chunk and summarize
            else:
                # Calculate effective chunk size
                effective_chunk_limit = int(max_input_tokens * 0.95)
                if effective_chunk_limit <= overlap:
                    overlap = max(10, int(effective_chunk_limit * 0.1))
                    
                effective_chunk_limit = max(effective_chunk_limit, intermediate_min_length + 10)
                effective_chunk_limit = min(effective_chunk_limit, max_input_tokens)
                
                # Create chunks
                text_chunks = create_text_chunks(current_text, global_tokenizer, effective_chunk_limit, overlap)
                
                if not text_chunks:
                    logging.warning("No text chunks were created.")
                    return ""
                
                logging.info(f"Generated {len(text_chunks)} chunks.")

                # *** MODIFICATION START: Select random 5 chunks if more than 5 are available ***
                if len(text_chunks) > 5:
                    logging.info(f"More than 5 chunks generated. Selecting 5 random chunks for processing.")
                    text_chunks = random.sample(text_chunks, 5)
                else:
                    logging.info(f"Processing all {len(text_chunks)} generated chunks (5 or fewer).")
                # *** MODIFICATION END ***
                
                logging.info(f"Processing {len(text_chunks)} selected chunks")
                
                # Process chunks in smaller batches to prevent OOM errors
                batch_size = 4 # This batch size is still relevant for the selected chunks
                chunk_summaries = []
                
                for i in range(0, len(text_chunks), batch_size):
                    batch = text_chunks[i:i+batch_size]
                    try:
                        batch_results = global_summarizer(
                            batch,
                            max_length=intermediate_max_length,
                            min_length=intermediate_min_length,
                            do_sample=False,
                            truncation=True
                        )
                        
                        # Extract valid summaries
                        for result in batch_results:
                            if (result and isinstance(result, dict) and 
                                result.get('summary_text', '').strip() and 
                                result.get('summary_text', '').lower() != "summarize:"):
                                chunk_summaries.append(result['summary_text'])
                    except Exception as batch_e:
                        logging.error(f"Error in batch {i//batch_size + 1}: {batch_e}")
                        continue # Continue with the next batch if one fails
                
                # Combine the summaries
                combined_summary = "\n".join(chunk_summaries)
                logging.info(f"Combined summaries from selected chunks: {len(combined_summary)} chars")
                
                # Safety check
                if not combined_summary.strip():
                    logging.warning("Combined summary from chunks is empty.")
                    return "" # If all selected chunks failed or produced empty summaries
                    
                current_text = combined_summary
                
                # Clean memory after each iteration
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
                
        except Exception as e:
            logging.error(f"Error in iteration {iteration}: {e}")
            return "" # Return empty string on error to maintain consistency
            
    # If we've hit max iterations but still have text that's too long,
    # perform a final forced summarization with truncation
    try:
        logging.info("Max iterations reached or loop exited. Performing final forced summarization on the current text.")
        # Ensure current_text is not excessively long for the final summarizer call, even if it's combined from few chunks
        # The model's tokenizer will handle truncation if current_text is still > max_input_tokens
        # However, to be safe and manage resources, we can still apply a sensible upper limit to what we pass.
        # This uses the model's actual max input tokens, which is more robust.
        # A common practice is to allow the `truncation=True` in the pipeline to handle this.
        # For very long `current_text` after iterations, an explicit pre-truncation might be useful.
        # The original code had `truncated_text = current_text[:max_input_tokens*4]`
        # We can retain this or rely on the pipeline's truncation.
        # For now, let's keep a similar explicit truncation as a safeguard.
        
        # Heuristic to decide if explicit truncation is needed before sending to final summarizer
        # If current_text is still very long (e.g., > 4x model_max_length), truncate it.
        # Otherwise, let the summarizer's internal truncation handle it.
        # This helps prevent passing extremely large strings if something unexpected happened.
        if len(global_tokenizer.encode(current_text)) > max_input_tokens * 4: # Arbitrary multiplier for "very long"
             # Truncate based on a multiple of model_max_length, then decode back to string
            logging.warning(f"Current text for final summarization is very long. Explicitly truncating to approx {max_input_tokens*4} tokens.")
            truncated_tokens = global_tokenizer.encode(current_text)[:max_input_tokens*4]
            current_text_for_final_summary = global_tokenizer.decode(truncated_tokens, skip_special_tokens=True)
        else:
            current_text_for_final_summary = current_text

        final_result = global_summarizer(
            current_text_for_final_summary, # Use the potentially truncated text
            max_length=final_max_length,
            min_length=final_min_length,
            do_sample=False,
            truncation=True # Ensure truncation is enabled in the summarizer
        )
        final_summary = final_result[0]['summary_text']
        
        if not final_summary.strip() or final_summary.lower() == "summarize:":
            return "" # Return empty if final summary is invalid
            
        return final_summary
    except Exception as final_e:
        logging.error(f"Error in final summarization: {final_e}")
        return "" # Return empty string on error