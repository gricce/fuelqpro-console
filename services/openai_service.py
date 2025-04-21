import os
import openai
import config
from models.nutrition_plan import NutritionPlan

def generate_nutrition_plan(user_profile, full_plan=False, log_message=print):
    """Generate a nutrition plan using OpenAI API"""
    try:
        openai.api_key = config.OPENAI_API_KEY
        log_message(">>> Generating nutrition plan with OpenAI")

        # Create prompt from user profile
        prompt = NutritionPlan.create_plan_prompt(user_profile, full_plan)

        # Set max tokens based on plan type
        max_tokens = 2000 if full_plan else 1000

        # Try GPT-4 first
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            plan = response.choices[0].message["content"].strip()
            log_message(">>> Nutrition plan generated with GPT-4")
            return plan if full_plan else truncate_response(plan, 1500)

        except Exception as gpt4_error:
            log_message(f">>> GPT-4 not available, falling back to GPT-3.5: {gpt4_error}")

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                plan = response.choices[0].message["content"].strip()
                log_message(">>> Nutrition plan generated with GPT-3.5")
                return plan if full_plan else truncate_response(plan, 1500)
            except Exception as gpt35_error:
                log_message(f">>> GPT-3.5 failed as well: {gpt35_error}")
                # Fall through to the hardcoded plan

    except Exception as e:
        log_message(f">>> ERROR generating nutrition plan: {str(e)}")
    
    # Hardcoded fallback plan
    log_message(">>> Using hardcoded fallback nutrition plan")
    return NutritionPlan.generate_fallback_plan(user_profile, full_plan)

def truncate_response(text, max_length=1500):
    """Truncate text to max_length characters"""
    if len(text) <= max_length:
        return text
    
    # Find the last paragraph break before max_length
    last_break = text.rfind("\n\n", 0, max_length)
    if last_break == -1:
        # If no paragraph break, find the last sentence
        last_break = text.rfind(". ", 0, max_length)
        if last_break == -1:
            # If no sentence break, just cut at max_length
            return text[:max_length] + "..."
        return text[:last_break+1] + "..."
    
    return text[:last_break] + "\n\n... (Plano completo não pode ser exibido. Digite 'pdf' para receber o plano completo)"

def verify_openai_api():
    """Verify that the OpenAI API key is valid"""
    try:
        api_key = config.OPENAI_API_KEY
        if not api_key:
            return "No OpenAI API key configured", 400
        
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        return f"OpenAI API key is valid. Response: {response.choices[0].message['content']}", 200
    except Exception as e:
        return f"OpenAI API key verification failed: {str(e)}", 400