import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import copy

# Inizializza il bot
intents = discord.Intents.default()
intents.message_content = True  # Permette al bot di leggere i contenuti dei messaggi

bot = commands.Bot(command_prefix="!", intents=intents)

# Variabili globali per il gioco
players = []
game_started = False
cards_per_player = 6
cards_folder = 'cards'  # Cartella contenente le immagini delle carte
storyteller_index = 0  # Indice per il narratore corrente
round_index = 0
storyteller_card = None  # Carta scelta dal narratore
hands = {}  # Mani di carte per ogni giocatore
played_cards = []  # Lista delle carte giocate da tutti i giocatori
played_cards_by_players = {}  # Lista delle carte giocate e associate ai giocatori (tranne il narratore)
storyteller_chose = False
votes = {}  # Dizionario che memorizza i voti
points = {}  # Punteggi per i giocatori

# Modifica la classe DynamicVoteButton per gestire i voti
class DynamicVoteButton(discord.ui.View):
    def __init__(self, ctx, num_buttons, storyteller, card_list):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.result = None
        self.voted_users = set()  # Set per tracciare chi ha votato
        self.storyteller = storyteller  # Aggiungi il narratore come attributo
        self.card_list = card_list
        global votes
        votes = {i: 0 for i in range(1, num_buttons + 1)}  # Inizializza i voti per la votazione
        self.create_buttons(num_buttons)

    # Funzione per creare i bottoni dinamicamente
    def create_buttons(self, num_buttons):
        for i in range(1, num_buttons + 1):
            self.add_item(VoteButton(label=str(i), button_id=i, parent_view=self, card_list=self.card_list))

# Modifica la classe VoteButton
class VoteButton(discord.ui.Button):
    def __init__(self, label, button_id, parent_view, card_list):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=str(button_id))
        self.button_id = button_id # num bottone (es 1, 2, ...)
        self.parent_view = parent_view
        global played_cards_by_players
        self.card_list = card_list

    async def callback(self, interaction: discord.Interaction):
        # Controlla se l'utente è il narratore
        if interaction.user == self.parent_view.storyteller:  # Verifica se l'utente è il narratore
            await interaction.response.send_message("Il narratore non può votare!", ephemeral=True)
            return
        
        # Controlla se l'utente ha già votato
        if interaction.user.id in self.parent_view.voted_users:
            await interaction.response.send_message("Hai già votato!", ephemeral=True)
            return
        
        #print("\n played_cards_by_players: ", played_cards_by_players)

        # Controlla se l'utente sta cercando di votare la propria carta
        user_card = played_cards_by_players.get(interaction.user)  # Ottieni la carta giocata dall'utente
        #print("\n user_card: ", user_card)
        #print("\n self.button_id: ", self.button_id)
        voted_card = self.card_list[self.button_id-1]
        #print("\n voted_card: ", voted_card)

        #if user_card and self.button_id == list(played_cards_by_players.values()).index(user_card) + 1:
        if user_card == voted_card:
            await interaction.response.send_message("Non puoi votare la tua stessa carta!", ephemeral=True)
            return

        # Gestisci il voto dell'utente
        self.parent_view.voted_users.add(interaction.user.id)  # Aggiungi l'utente alla lista di chi ha votato
        votes[self.button_id] += 1  # Incrementa il voto per la carta scelta
        await interaction.response.send_message(f"Hai votato per la carta {self.button_id}!", ephemeral=True)

        # Controlla se tutti i giocatori hanno votato
        if len(self.parent_view.voted_users) == len(players) - 1:  # Escludi il narratore
            await self.parent_view.ctx.send("Tutti hanno votato! Calcoliamo i punteggi...")
            await calculate_scores(self.parent_view.ctx)  # Chiama il calcolo dei punteggi




# Funzione per caricare le carte
def load_cards():
    return [f for f in os.listdir(cards_folder) if os.path.isfile(os.path.join(cards_folder, f))]

deck = load_cards()
complete_deck = load_cards()


# Funzione per gestire il turno
async def round(ctx: commands.Context):
    global round_index, storyteller_index
    # Selezione del narratore
    # Se è il turno iniziale 
    if round_index == 0:
        storyteller = random.choice(players)  # Seleziona un narratore casuale dalla lista dei giocatori
        storyteller_index = players.index(storyteller)  # Ottieni l'indice del narratore casuale
        await send_message(ctx, f"La partita ha inizio! {storyteller.display_name} è stato scelto come narratore! Ora descrivi la carta che vuoi giocare con !describe.")
    # Per i turni successivi, ruota tra i giocatori
    else:
        if storyteller_index == len(players)-1:  # Se siamo alla fine della lista di giocatori, ricomincia daccapo
            storyteller_index = 0
        else:
            storyteller_index += 1  # Altrimenti passa al giocatore affianco
        storyteller = players[storyteller_index]
        await send_message(ctx, f"Inizia un nuovo round! {storyteller.display_name} è il nuovo narratore! Ora descrivi la carta che vuoi giocare con !describe.")

    # Distribuzione carte uniche ai giocatori
    for player in players:
        hand = random.sample(deck, cards_per_player)  # Rimozione carte dal mazzo man mano che vengono distribuite
        hands[player] = hand
        for card in hand:
            deck.remove(card)

    # Manda le immagini delle carte a ciascun giocatore in privato
    for player, hand in hands.items():
        await player.send(f"Questo è il turno {round_index + 1}. Preparati!")
        for card_image in hand:
            file_path = os.path.join(cards_folder, card_image)
            await player.send(file=discord.File(file_path))
        print(f"Turno {round_index + 1}.")
        print(f"{player.display_name} ha ricevuto le seguenti carte: {', '.join(hand)}.")


# Funzione per inviare messaggi sia per i comandi con prefisso che Slash Command
async def send_message(ctx, message):
    # Se è un comando Slash (interazione), usa followup per eventuali risposte aggiuntive
    if ctx.interaction:
        if not ctx.interaction.response.is_done():
            await ctx.interaction.response.send_message(message)
        else:
            await ctx.interaction.followup.send(message)
    else:
        # Se è un comando con prefisso (!comando), usa ctx.send()
        await ctx.send(message)



@bot.hybrid_command(name="describe_and_choose", description="Scegli il numero della carta e descrivila.")
async def describe_and_choose(ctx: commands.Context, numero_carta: int, description: str):
    global storyteller_index, storyteller_card, hands, storyteller_chose
    storyteller = players[storyteller_index]

    # Controllo se l'autore del comando è il narratore
    if ctx.author.id != storyteller.id:
        await send_message(ctx, "Solo il narratore può scegliere e descrivere la carta in questa fase.")
        return
    
    if storyteller_chose:
        await send_message(ctx, "Il narratore ha già scelto e descritto la carta.")
        return

    # Verifica che il numero della carta sia valido
    hand = hands[storyteller]
    if numero_carta < 1 or numero_carta > len(hand):
        await send_message(ctx, "Numero di carta non valido. Scegli un numero valido dalla tua mano.")
        return

    # Selezione della carta
    storyteller_chose = True
    storyteller_card = hand.pop(numero_carta - 1)  # Rimuove la carta dalla mano
    played_cards.append((ctx.author, storyteller_card))  # Aggiunge la carta giocata
    await ctx.interaction.response.send_message(f"{storyteller.display_name} ha scelto e descritto la sua carta: '{description}'.\n" 
                                                "Gli altri giocatori ora devono scegliere una carta che si adatta alla descrizione usando !playcard [numero_carta].")



# Comando per i giocatori per scegliere una carta
@bot.hybrid_command(name="playcard", description="Gioca una carta")
async def play_card(ctx: commands.Context, numero_carta: int):
    global storyteller_index, hands, played_cards, played_cards_by_players
    storyteller = players[storyteller_index]

    # Controllo se l'autore del comando è il narratore
    if ctx.author == storyteller:
        await send_message(ctx, "Il narratore non può giocare una carta in questa fase.")
        return
    
    if not storyteller_chose:
        await send_message(ctx, "Il narratore non ha ancora descritto e/o scelto la carta da giocare.")
        return

    # Verifica che il numero della carta sia valido
    hand = hands[ctx.author]
    if numero_carta < 1 or numero_carta > len(hand):
        await send_message(ctx, "Numero di carta non valido. Scegli un numero valido dalla tua mano.")
        return

    # Selezione della carta da parte del giocatore
    carta_scelta = hand.pop(numero_carta - 1)  # Rimuove la carta dalla mano del giocatore
    played_cards.append((ctx.author, carta_scelta))  # Aggiunge la carta giocata
    played_cards_by_players[ctx.author] = carta_scelta
    await send_message(ctx, f"{ctx.author.display_name} ha giocato una carta.")

    # Controllo se tutti i giocatori (escluso il narratore) hanno giocato una carta
    if len(played_cards) == len(players):
        await show_cards(ctx)


# Funzione per mostrare le carte mescolate
async def show_cards(ctx: commands.Context):
    global played_cards
    # Mescola le carte
    random.shuffle(played_cards)

    # Prepara una lista di file delle immagini delle carte e testo da inviare in un solo messaggio
    carte_da_mostrare = []
    played_card_names = []
    messaggio_carte = "Ecco le carte:\n"

    # Prepara il messaggio contenente i numeri delle carte
    for i, (player, card) in enumerate(played_cards, start=1):
        file_path = os.path.join(cards_folder, card)
        carte_da_mostrare.append(discord.File(file_path))  # Aggiungi il file della carta alla lista
        played_card_names.append(card)

    # Invia tutte le carte in un solo messaggio
    await ctx.send(messaggio_carte, files=carte_da_mostrare)

    # Crea i bottoni dinamicamente in base al numero di carte
    num_buttons = len(played_cards)
    storyteller = players[storyteller_index]
    view = DynamicVoteButton(ctx, num_buttons, storyteller, played_card_names)
    await ctx.send("Scegli la carta che pensi sia quella del narratore cliccando su un bottone:", view=view)

    # Aggiungi la logica per gestire i voti al termine della votazione
    await view.wait()  # Aspetta che i voti siano stati espressi
    await calculate_scores(ctx)


# Funzione per calcolare i punti
async def calculate_scores(ctx: commands.Context):
    global storyteller_card, played_cards, votes, points, storyteller_index, deck, round_index, storyteller_chose
    storyteller = players[storyteller_index]
    #print("\n Contenuto di votes:", votes)

    # Trova l'indice della carta del narratore
    storyteller_card_index = next(i for i, (player, card) in enumerate(played_cards, start=1) if player == storyteller)

    #print("\n storyteller_card_index:", storyteller_card_index)

    # Controlla se tutti o nessuno ha votato la carta del narratore
    if votes[storyteller_card_index] == 0 or votes[storyteller_card_index] == len(players) - 1:
        # Nessuno o tutti hanno votato la carta del narratore
        for player in players:
            if player != storyteller:
                points[player] = points.get(player, 0) + 2  # Ogni altro giocatore guadagna 2 punti
        await send_message(ctx, "Nessuno o tutti hanno votato la carta del narratore. Il narratore ottiene 0 punti, gli altri giocatori guadagnano 2 punti ciascuno.")
    else:
        # Alcuni hanno votato correttamente
        points[storyteller] = points.get(storyteller, 0) + 3  # Il narratore guadagna 3 punti
        for player, card in played_cards:
            if player != storyteller and votes[played_cards.index((player, card)) + 1] > 0:
                points[player] = points.get(player, 0) + 1  # Giocatori che ricevono voti guadagnano 1 punto per voto
        await send_message(ctx, "Il narratore e chi ha votato correttamente guadagnano 3 punti.")

    # Mostra i punteggi finali
    await display_scores(ctx)

    # Check fine partita
    # Verifica se qualcuno ha raggiunto i 30 punti
    for player, score in points.items():
        if score >= 4:  # Cambia a 30 per il gioco completo
            await send_message(ctx, f"{player.display_name} ha raggiunto 30 punti e vince la partita!")
            game_started = False
            return  # Termina il gioco
    # Verifica se il mazzo è esaurito
    if len(deck) < cards_per_player * len(players):
        await send_message(ctx, "Il mazzo è esaurito. La partita finisce qui!")
        # Trova il giocatore con più punti
        highest_score = max(points.values())
        winners = [player.display_name for player, score in points.items() if score == highest_score]
        if len(winners) > 1:
            await send_message(ctx, f"La partita è finita! I vincitori sono: {', '.join(winners)} con {highest_score} punti!")
        else:
            await send_message(ctx, f"La partita è finita! Il vincitore è {winners[0]} con {highest_score} punti!")
        game_started = False
        return  # Termina il gioco

    # Se la partita non è finita, inizia un nuovo round: ripristina il gioco per il turno successivo
    round_index += 1
    storyteller_card = None
    hands.clear()
    played_cards.clear()
    played_cards_by_players.clear()
    storyteller_chose = False
    votes.clear()
    deck = copy.deepcopy(complete_deck)

    await round(ctx)


# Funzione per mostrare i punteggi
async def display_scores(ctx: commands.Context):
    global points
    punteggi = "```md\n"
    punteggi += "| Giocatore         | Punti |\n"
    punteggi += "|-------------------|-------|\n"
    for player in players:
        punteggi += f"| {player.display_name:<17} | {points.get(player, 0):<5} |\n"
    punteggi += "```"
    await send_message(ctx, f"Punteggi attuali:\n{punteggi}")


# Evento: quando il bot è pronto
@bot.event
async def on_ready():
    print(f'Bot connesso come {bot.user}')
    await bot.tree.sync()

# Setup di gioco
# Comando per iniziare il gioco: risposta a "!dixit" o "/dixit"
@bot.hybrid_command(name="dixit", description="Inizia una nuova partita di Dixit")
async def dixit_game(ctx: commands.Context):
    global players, game_started
    if game_started:
        await send_message(ctx, "C'è già una partita in corso!")
    else:
        players = []
        game_started = True
        storyteller_index = 0
        await send_message(ctx, "Partita di Dixit iniziata! Usate !join per partecipare e confermate con !begin per chiudere le partecipazioni.")

# Comando per unirsi alla partita: risposta a "!join" o "/join"
@bot.hybrid_command(name="join", description="Unisciti alla partita")
async def join_game(ctx: commands.Context):
    if game_started:
        player = ctx.author
        if player not in players:
            players.append(player)
            await send_message(ctx, f"{player.display_name} si è unito alla partita!")
            print(f"{player.display_name} si è unito alla partita.")
        else:
            await send_message(ctx, f"{player.display_name} è già nella partita!")
    else:
        await send_message(ctx, "Nessuna partita attiva. Usa !startgame per iniziarne una.")


# Comando per iniziare ufficialmente la partita: risposta a "/start"
@bot.hybrid_command(name="start", description="Inizia ufficialmente la partita")
async def start_game(ctx: commands.Context):
    global game_started
    if not game_started:
        await send_message(ctx, "Nessuna partita attiva. Usa !startgame per iniziarne una.")
    elif len(players) < 1:
        await send_message(ctx, "Servono almeno 3 giocatori per iniziare la partita.")
    else:
        await round(ctx)  # Chiama la funzione per gestire il turno

# Comando per terminare forzatamente la partita
@bot.hybrid_command(name="endgame", description="Termina la partita attuale")
async def end_game(ctx: commands.Context):
    global game_started
    player = ctx.author
    if not game_started:
        await send_message(ctx, f"Non c'è nessuna partita da interrompere.")
    else:
        await send_message(ctx, f"Partita interrotta da {player.display_name}.")
        game_started = False  # La partita è finita, non è più attiva



# Avvia il bot con il token
bot.run('TOKEN')


# Per ogni turno
# -scelta narratore
# -distribuzione carte: ognuno riceve 6 carte in privato 
# -il narratore dà l'indizio
# -ogni giocatore sceglie la carta che matcha di più
# -il narratore ritira le carte scelte e le mischia con la sua
# -il narratore espone tutte le carte sul tavolo
# -ogni giocatore (tranne il narratore) vota segretamente con il proprio sgenalino quale carta pensa che sia quella del narratore
# -quando tutti hanno votato, si scoprono i segnalini e il narratore rivela la sua carta: 
#   Per il narratore:
#       1) se tutti/nessuno ha votato la carta del narratore, allora il narratore fa 0 punti, gli altri fanno 2 punti;
#       2) se qualcuno (>0 e <tot) ha votato la carta del narratore, allora il narratore fa 3 punti e quel qualcuno fa 2 punti (caso 2);
#   Per i giocatori:
#       3) se il giocatore indovina la carta del narattore, fa 2 punti;
#       4) se il giocatore non indovina la carta del narratore (e qualcuno l'ha indovinata, caso 2), fa 0 punti;
#       + se la carta del giocatore è stata votata, fa 1 punto per ogni voto ricevuto;
# Alla fine del turno
# -si cestinano le carte già usate
# -il narratore diventa quello accanto (in senso orario, quindi in ordine temporale di join al gioco)
# Condizioni di fine gioco
# 1) vince il primo che arriva a 30 punti;
# 2) il deck finisce e vince il giocatore con più punti
