from twilio.twiml.messaging_response import MessagingResponse
from models.user import UserProfile
from services.openai_service import generate_nutrition_plan
from services.pdf_service import generate_nutrition_plan_pdf
from services.storage_service import upload_pdf_to_storage
from services.firebase_service import log_interaction, upload_pdf_to_firebase, get_user_data
import config
import datetime


def process_whatsapp_message(sender, incoming_msg, log_message=print):
    """Process an incoming WhatsApp message and return the appropriate response"""
    resp = MessagingResponse()
    
    try:
        # Get user data from storage
        user_data = UserProfile.get_user(sender)
        log_message(f">>> Current user step: {user_data['step']}")
        
        # Get Firebase data for returning users
        firebase_data = get_user_data(sender)
        
        # Welcome back logic for returning users
        if firebase_data and firebase_data.get('created_at') and not firebase_data.get('reset_at'):
            # This is a returning user
            created_at = firebase_data.get('created_at')
            current_time = datetime.datetime.now(created_at.tzinfo)
            
            # If they haven't interacted in more than a week
            last_interaction = firebase_data.get('last_interaction', created_at)
            days_since_interaction = (current_time - last_interaction).days
            
            if days_since_interaction > 7:
                name = firebase_data.get('profile', {}).get('name', '')
                resp.message(f"Olá {name}, bem-vindo(a) de volta ao FuelQ Pro! É bom ver você novamente. Digite 'planos' para ver seus planos anteriores ou 'visualizar' para criar um novo plano.")
                log_interaction(sender, 'outgoing', 'welcome_back', str(resp), log_message)
                return str(resp)
        
        # Check if we're asking about PDF option
        if user_data.get("asking_pdf", False):
            UserProfile.set_asking_pdf(sender, False)
            
            if incoming_msg.lower() in ["sim", "s", "yes", "y"]:
                # User wants PDF
                pdf_bytes, pdf_url = generate_nutrition_plan_pdf(user_data.get("profile", {}), log_message)
                if pdf_bytes and pdf_url:
                    resp.message(f"Aqui está o link para seu plano nutricional completo em PDF:\n\n{pdf_url}\n\nEste link ficará disponível por 7 dias.")
                    log_message(f">>> Sent PDF link to {sender}: {pdf_url}")
                else:
                    resp.message("Desculpe, ocorreu um erro ao gerar o PDF. Por favor, tente novamente mais tarde digitando 'pdf'.")
                    log_message(f">>> Failed to generate or upload PDF for {sender}")
            else:
                # User doesn't want PDF
                resp.message("Tudo bem! Se desejar o plano em PDF no futuro, digite 'pdf'.")
                log_message(f">>> User declined PDF plan for {sender}")
            return str(resp)
        
        # Process commands
        if incoming_msg.lower() == "visualizar":
            if len(user_data.get("profile", {})) < len(config.STEPS):
                resp.message("Você ainda não completou seu perfil. Por favor, continue respondendo as perguntas.")
                log_message(f">>> Profile incomplete, prompting user to complete it")
            else:
                log_message(f">>> Generating personalized nutrition plan for {sender}")
                # Generate a personalized nutrition plan
                plan = generate_nutrition_plan(user_data.get("profile", {}), log_message=log_message)
                
                # Ask if they want a PDF version
                UserProfile.set_asking_pdf(sender, True)
                
                # Add a question about the PDF
                pdf_question = "\n\nGostaria de receber este plano em formato PDF? (Sim/Não)"
                
                # Ensure we don't exceed WhatsApp character limits
                message_limit = 1500 - len(pdf_question)
                if len(plan) > message_limit:
                    from services.openai_service import truncate_response
                    plan = truncate_response(plan, message_limit)
                
                resp.message(plan + pdf_question)
                log_message(f">>> Sent nutrition plan and asked about PDF for {sender}")
        elif incoming_msg.lower() == "pdf":
            if not user_data.get("profile") or len(user_data.get("profile", {})) < len(config.STEPS):
                resp.message("Você precisa completar seu perfil e gerar um plano básico primeiro. Digite 'reiniciar' para começar.")
            else:
                # Generate and upload PDF
                pdf_bytes, pdf_url = generate_nutrition_plan_pdf(user_data.get("profile", {}), log_message)
                if pdf_bytes and pdf_url:
                    resp.message(f"Aqui está o link para seu plano nutricional completo em PDF:\n\n{pdf_url}\n\nEste link ficará disponível por 7 dias.")
                    log_message(f">>> Sent PDF link to {sender}: {pdf_url}")
                else:
                    resp.message("Desculpe, ocorreu um erro ao gerar o PDF. Por favor, tente novamente mais tarde.")
                    log_message(f">>> Failed to generate PDF for {sender}")
        elif incoming_msg.lower() == "planos" or incoming_msg.lower() == "meus planos":
            # Get user's previous plans from Firebase
            if not firebase_data or not firebase_data.get('pdf_plans'):
                resp.message("Você ainda não tem planos salvos. Digite 'visualizar' para gerar seu primeiro plano.")
            else:
                plans = firebase_data.get('pdf_plans', [])
                plan_list = "\n\n".join([
                    f"{i+1}. Plano criado em {plan.get('created_at').strftime('%d/%m/%Y')}: {plan.get('url')}"
                    for i, plan in enumerate(plans[:5])  # Show last 5 plans
                ])
                resp.message(f"Seus planos nutricionais:\n\n{plan_list}\n\nDigite 'visualizar' para gerar um novo plano.")
        elif incoming_msg.lower() == "reiniciar":
            log_message(f">>> User profile reset: {sender}")
            UserProfile.reset_user(sender)
            resp.message("Perfil reiniciado. Vamos começar de novo!\n\n" + config.STEPS[0][1])
            log_message(f">>> Sent reset confirmation to {sender}")
        elif incoming_msg.lower() == "ok":
            if len(user_data.get("profile", {})) < len(config.STEPS):
                resp.message("Você ainda não completou seu perfil. Por favor, continue respondendo as perguntas.")
                log_message(f">>> Profile incomplete, prompting user to complete it")
            else:
                log_message(f">>> Generating personalized nutrition plan for {sender}")
                # Generate a personalized nutrition plan
                plan = generate_nutrition_plan(user_data.get("profile", {}), log_message=log_message)
                
                # Ask if they want a PDF version
                UserProfile.set_asking_pdf(sender, True)
                
                # Add a question about the PDF
                pdf_question = "\n\nGostaria de receber este plano em formato PDF? (Sim/Não)"
                
                # Ensure we don't exceed WhatsApp character limits
                message_limit = 1500 - len(pdf_question)
                if len(plan) > message_limit:
                    from services.openai_service import truncate_response
                    plan = truncate_response(plan, message_limit)
                
                resp.message(plan + pdf_question)
                log_message(f">>> Sent nutrition plan and asked about PDF for {sender}")
        else:
            # Regular conversation flow
            current_step = user_data.get("step", 0)
            
            if current_step < len(config.STEPS):
                field_key, _ = config.STEPS[current_step]
                
                # Update user profile with this response
                UserProfile.update_profile(sender, field_key, incoming_msg)
                log_message(f">>> Stored '{incoming_msg}' as {field_key}")
                
                # Move to the next step
                next_step = UserProfile.advance_step(sender)
                log_message(f">>> Advanced to step {next_step}")
                
                # Send the next question or summary
                if next_step < len(config.STEPS):
                    resp.message(config.STEPS[next_step][1])
                    log_message(f">>> Sent question for step {next_step}: '{config.STEPS[next_step][1]}'")
                else:
                    # Generate summary after the last question
                    from models.nutrition_plan import NutritionPlan
                    summary = NutritionPlan.format_user_profile(user_data["profile"])
                    resp.message(f"Obrigado! Aqui está o resumo do seu perfil:\n\n{summary}\n\nVerifique se os dados estão corretos e se estiver tudo certo, digite OK, para receber o seu plano, ou reiniciar para recomeçar o processo.")
                    log_message(f">>> Sent profile summary to {sender}")
            else:
                resp.message("Digite 'visualizar' para receber sua estratégia, 'pdf' para receber o plano em PDF, ou 'reiniciar' para começar novamente.")
                log_message(f">>> Sent default message to {sender}")
    
    except Exception as e:
        log_message(f">>> ERROR: {str(e)}")
        resp.message("Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.")
    
    # Log the interaction after processing
    log_interaction(sender, 'outgoing', incoming_msg, str(resp), log_message)
    return str(resp)