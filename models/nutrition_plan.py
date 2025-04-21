import config

class NutritionPlan:
    """Nutrition plan generation and management"""
    
    @staticmethod
    def format_user_profile(profile):
        """Format user profile data for display"""
        return "\n".join([f"{config.LABELS.get(k, k)}: {v}" for k, v in profile.items()])
    
    @staticmethod
    def create_plan_prompt(profile, full_plan=False):
        """Create prompt for OpenAI API"""
        profile_text = NutritionPlan.format_user_profile(profile)
        
        # Adjust prompt based on whether this is for the full plan or truncated version
        length_instruction = "detalhado e completo" if full_plan else "conciso para caber em uma mensagem de WhatsApp (máximo 1500 caracteres)"

        prompt = f"""
        Crie um plano de nutrição personalizado para esportistas baseado nesse perfil:

        {profile_text}

        O plano deve incluir:
        1. Recomendações gerais baseadas no perfil
        2. Sugestões de alimentação pré, durante e pós treino
        3. Dicas para evitar cãibras (se aplicável)
        4. Estratégia de hidratação
        5. Formato {profile.get('plan_type', 'Diário')}

        O plano deve ser {length_instruction}.
        """
        
        return prompt
    
    @staticmethod
    def generate_fallback_plan(profile, full_plan=False):
        """Generate a fallback nutrition plan if API calls fail"""
        # Extract key profile elements
        name = profile.get('name', '')
        sports = profile.get('sports', '').lower()
        has_cramps = profile.get('cramps', '').lower() == 'sim'
        plan_type = profile.get('plan_type', 'Diário').lower()
        
        # Basic recommendations based on sport
        sport_recommendations = {
            'ciclismo': "Como ciclista, foque em carboidratos complexos e proteínas para recuperação.",
            'corrida': "Como corredor, priorize carboidratos e proteínas magras.",
            'natação': "Como nadador, equilibre carboidratos e proteínas."
        }
        
        # Default if sport not found
        sport_text = next((v for k, v in sport_recommendations.items() if k in sports), 
                         "Foque em carboidratos complexos e proteínas para recuperação.")
        
        # Cramp recommendations
        cramp_text = "\n\n🔹 DICAS PARA EVITAR CÃIBRAS:\n- Aumente magnésio e potássio (banana, abacate)\n- Hidrate-se bem\n- Faça alongamentos" if has_cramps else ""
        
        # Create the plan
        fallback_plan = f"""🍎 PLANO NUTRICIONAL 🍎

Olá {name}! Seu plano {plan_type.lower()}:

🔹 GERAL:
{sport_text}
- 5-6 refeições pequenas ao dia
- 2-3 litros de água diários

🔹 PRÉ-TREINO:
- Carboidratos: batata doce, aveia
- Proteína: frango, ovo ou whey

🔹 DURANTE:
- Água com eletrólitos
- Gel para treinos >1h

🔹 PÓS-TREINO:
- Whey protein
- Carboidratos: banana, mel{cramp_text}

🔹 HIDRATAÇÃO:
- 500ml água 2h antes
- 150-200ml a cada 15-20min
- 500ml após treino

Consulte um nutricionista!
"""
        
        # Add more detailed information for the full plan
        if full_plan:
            fallback_plan += """
🔹 PLANO DETALHADO:

Café da manhã:
- 1 xícara de aveia cozida com frutas
- 2 ovos ou 30g de whey protein
- 1 fruta (banana ou maçã)

Lanche da manhã:
- Iogurte natural com granola
- Punhado de castanhas

Almoço:
- 150g de proteína magra (frango, peixe)
- 1 xícara de arroz integral ou batata doce
- Vegetais variados (2 xícaras)
- 1 colher de azeite de oliva

Lanche pré-treino (1-2h antes):
- 1 banana
- 1 torrada com mel
- 200ml de água

Durante treino:
- 500-750ml de água com eletrólitos por hora
- Gel energético a cada 45-60min para treinos longos

Pós-treino imediato:
- 30g de whey protein
- 1 banana ou 1 colher de mel

Jantar:
- 150g de proteína magra
- Vegetais variados
- 1/2 xícara de carboidratos complexos

Suplementação recomendada:
- Magnésio: 300-400mg/dia (especialmente se tem cãibras)
- Vitamina D: 1000-2000 UI/dia
- Eletrólitos para reposição durante treinos intensos

Esse plano deve ser adaptado conforme suas necessidades calóricas específicas e ajustado com o acompanhamento de um nutricionista esportivo.
"""
        
        return fallback_plan