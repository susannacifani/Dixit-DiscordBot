import openai

# Inserisci la tua API key di OpenAI qui
openai.api_key = 'KEY'

# Funzione per inviare una richiesta all'API di OpenAI usando gpt-3.5-turbo
def chiedi_openai(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Utilizziamo gpt-3.5-turbo
        messages=[  # Il modello chat richiede il contesto sotto forma di lista di messaggi
            {"role": "system", "content": "Sei un narratore creativo e fantasioso. Descrivi una carta di Dixit come se stessi raccontando una storia misteriosa e affascinante."},  # Puoi definire il ruolo del modello
            {"role": "user", "content": prompt}  # Messaggio inviato dall'utente
        ],
        max_tokens=50,  # Numero massimo di token nella risposta
        n=1,  # Numero di risposte da generare
        stop=None,  # Puoi specificare una stringa per fermare l'output
        temperature=0.8,  # Grado di creatività della risposta (0.0 a 1.0)
    )
    return response['choices'][0]['message']['content'].strip()

# Esempio di utilizzo
prompt = "Descrivi una carta con un castello fluttuante sopra le nuvole."
risposta = chiedi_openai(prompt)
print(risposta)




