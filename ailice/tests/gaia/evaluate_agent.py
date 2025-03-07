import json
import re
import logging
import os
from pathlib import Path
from typing import Dict, List, Union, Optional
from datasets import load_dataset
import requests
import json
from termcolor import colored

def chat_with_ailice(message: str) -> str:
    data = {
        "message": message
    }
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.get("http://localhost:5000/new_chat", headers=headers)
    response = requests.post("http://localhost:5000/chat", json=data, headers=headers, stream=True)
    full_response = ""
    current_role = ""
    current_msg = ""
    ret = ""
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                line = line[6:]
            msg = json.loads(line)
            if "open" == msg['action']:
                current_role = msg['role']
                current_msg = msg['message']
            elif "append" == msg['action']:
                current_msg += msg['message']
            elif "close" == msg['action']:
                current_msg += msg['message']
                print(colored(current_role, "green"),": ")
                print(current_msg)
            
            if ("user-ailice" == msg['msgType']) and ("ASSISTANT_AIlice" == msg["role"]):
                ret += msg["message"]
    
    return ret

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gaia_evaluation.log'),
        logging.StreamHandler()
    ]
)

def detect_answer_type(answer: str) -> str:
    '''
    Detect the type of answer based on its content.
    
    Args:
        answer: The answer string to analyze
    Returns:
        'number', 'list', or 'string'
    '''
    # Try to convert to number
    try:
        float(answer.replace(',', '').strip())
        return 'number'
    except ValueError:
        pass
    
    # Check if it's a comma-separated list
    if ',' in answer:
        return 'list'
    
    # Default to string
    return 'string'

def normalize_answer(answer: str, answer_type: Optional[str] = None) -> Union[str, float, List[str]]:
    '''
    Normalize the answer based on its type.
    
    Args:
        answer: The answer to normalize
        answer_type: Optional type override ('string', 'number', 'list')
    Returns:
        Normalized answer
    '''
    if not answer:
        return answer

    # Detect type if not provided
    if answer_type is None:
        answer_type = detect_answer_type(answer)

    if answer_type == 'number':
        try:
            # Remove any non-numeric characters except decimal point
            clean_answer = re.sub(r'[^0-9.-]', '', answer)
            return float(clean_answer)
        except ValueError:
            logging.error(f"Failed to normalize number: {answer}")
            return answer

    elif answer_type == 'list':
        try:
            items = [item.strip() for item in answer.split(',')]
            # Normalize each item in the list
            normalized_items = []
            for item in items:
                if detect_answer_type(item) == 'number':
                    try:
                        normalized_items.append(float(re.sub(r'[^0-9.-]', '', item)))
                    except ValueError:
                        normalized_items.append(item.lower())
                else:
                    # Remove articles and normalize string
                    item = re.sub(r'\b(a|an|the)\b', '', item.lower())
                    normalized_items.append(' '.join(item.split()))
            return normalized_items
        except Exception as e:
            logging.error(f"Failed to normalize list: {answer}, error: {e}")
            return []

    else:  # string type
        # Remove articles and extra whitespace
        clean_answer = re.sub(r'\b(a|an|the)\b', '', answer.lower())
        return ' '.join(clean_answer.split())

def build_prompt(question: str, files: Optional[Dict[str, str]] = None) -> str:
    '''
    Build the complete prompt with system prompt and file information.
    
    Args:
        question: The question content
        files: Optional dict of {file_name: file_path}
    Returns:
        Complete prompt
    '''
    system_prompt = '''System prompt: You are a general AI assistant. I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER]'''
    prompt = f"{system_prompt}\n\n{question}"
    
    if files:
        prompt += "\n\nRelevant files for this task:"
        for fname, fpath in files.items():
            if not os.path.exists(fpath):
                logging.warning(f"File not found: {fpath}")
                continue
            prompt += f"\n- {fname}: {fpath}"
    
    return prompt

def extract_answer(response: str) -> str:
    '''
    Extract the final answer from the response.
    
    Args:
        response: The complete response string
    Returns:
        The extracted answer or empty string
    '''
    match = re.search(r'FINAL ANSWER:\s*(.*?)(?:\n|$)', response, re.IGNORECASE | re.DOTALL)
    if not match:
        logging.warning(f"No 'FINAL ANSWER:' found in response: {response}")
        return ""
    return match.group(1).strip()

def evaluate_answer(model_answer: Union[str, float, List], 
                   ground_truth: Union[str, float, List]) -> float:
    '''
    Evaluate a single answer against the ground truth.
    
    Args:
        model_answer: The normalized model answer
        ground_truth: The normalized ground truth
    Returns:
        1.0 for match, 0.0 otherwise
    '''
    try:
        if isinstance(ground_truth, list) and isinstance(model_answer, list):
            return float(sorted(model_answer) == sorted(ground_truth))
        elif isinstance(ground_truth, (int, float)) and isinstance(model_answer, (int, float)):
            # Allow small numerical differences
            return float(abs(float(model_answer) - float(ground_truth)) < 1e-6)
        else:
            return float(str(model_answer).strip() == str(ground_truth).strip())
    except Exception as e:
        logging.error(f"Error in answer evaluation: {e}")
        return 0.0

def evaluate_agent(dataset, agent_function) -> Dict:
    '''
    Evaluate the agent on the dataset.
    
    Args:
        dataset: The GAIA dataset
        agent_function: Function that takes a prompt and returns a response
    Returns:
        Evaluation results including scores and details
    '''
    scores = {'1': 0, '2': 0, '3': 0}
    counts = {'1': 0, '2': 0, '3': 0}
    details = []
    
    for entry in dataset:
        try:
            # Prepare files dict if present
            files = None
            if entry['file_name'] and entry['file_path']:
                files = {entry['file_name']: entry['file_path']}
            
            # Build prompt and get response
            prompt = build_prompt(entry['Question'], files)
            response = agent_function(prompt)
            
            # Extract and normalize answers
            model_answer = extract_answer(response)
            answer_type = detect_answer_type(entry['Final answer'])
            norm_model_answer = normalize_answer(model_answer, answer_type)
            norm_ground_truth = normalize_answer(entry['Final answer'], answer_type)
            
            # Evaluate answer
            score = evaluate_answer(norm_model_answer, norm_ground_truth)
            
            # Update scores
            level = str(entry['Level'])
            scores[level] += score
            counts[level] += 1
            
            # Record details
            details.append({
                'task_id': entry['task_id'],
                'level': level,
                'question': entry['Question'],
                'model_answer': model_answer,
                'normalized_model_answer': norm_model_answer,
                'ground_truth': entry['Final answer'],
                'normalized_ground_truth': norm_ground_truth,
                'score': score,
                'error': None
            })
            
        except Exception as e:
            logging.error(f"Error processing entry {entry.get('task_id', 'unknown')}: {e}")
            details.append({
                'task_id': entry.get('task_id', 'unknown'),
                'level': entry.get('Level', 'unknown'),
                'error': str(e),
                'score': 0
            })
    
    # Calculate final scores
    total_count = sum(counts.values())
    result = {
        'overall_score': sum(scores.values()) / total_count if total_count > 0 else 0.0,
        'level_1_score': scores['1'] / counts['1'] if counts['1'] > 0 else 0.0,
        'level_2_score': scores['2'] / counts['2'] if counts['2'] > 0 else 0.0,
        'level_3_score': scores['3'] / counts['3'] if counts['3'] > 0 else 0.0,
        'details': details
    }
    
    return result

def main():
    """
    Main function to run the GAIA evaluation
    """
    logging.info("Starting GAIA evaluation...")
    
    # Load dataset
    try:
        ds = load_dataset("gaia-benchmark/GAIA", '2023_all')
        logging.info(f"Loaded dataset with {len(ds['validation'])} validation entries")
    except Exception as e:
        logging.error(f"Failed to load dataset: {e}")
        return

    # Run evaluation on validation set
    results = evaluate_agent(ds['validation'], chat_with_ailice)
    
    # Save results
    output_file = 'evaluation_results.json'
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Results saved to {output_file}")
    except Exception as e:
        logging.error(f"Failed to save results: {e}")

    # Print summary
    print("\nEvaluation Summary:")
    print(f"Overall Score: {results['overall_score']:.2%}")
    print(f"Level 1 Score: {results['level_1_score']:.2%}")
    print(f"Level 2 Score: {results['level_2_score']:.2%}")
    print(f"Level 3 Score: {results['level_3_score']:.2%}")

if __name__ == "__main__":
    main()
