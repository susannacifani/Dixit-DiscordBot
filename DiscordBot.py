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
storyteller_described = False
storyteller_chose = False
votes = {}  # Dizionario che memorizza i voti
points = {}  # Punteggi per i giocatori


# Funzione per caricare le carte
def load_cards():
    return [f for f in os.listdir(cards_folder) if os.path.isfile(os.path.join(cards_folder, f))]

deck = load_cards()
complete_deck = load_cards()


# Funzione per gestire il turno
async def round(ctx):
    global round_index, storyteller_index
    # Selezione del narratore
    # Se è il turno iniziale 
    if round_index == 0:
        storyteller = random.choice(players) # Seleziona un narratore casuale dalla lista dei giocatori
        storyteller_index = players.index(storyteller)  # Ottieni l'indice del narratore casuale
        await ctx.send(f"La partita ha inizio! {storyteller.display_name} è stato scelto come narratore! Ora descrivi la carta che vuoi giocare con !describe.")
    # Per i turni successivi, ruota tra i giocatori
    else:
        if storyteller_index == len(players)-1: # Se siamo alla fine della lista di giocatori, ricomincia daccapo
            storyteller_index = 0
        else:
            storyteller_index = storyteller_index+1 # Altrimenti passa al giocatore affianco
        storyteller = players[storyteller_index]
        await ctx.send(f"Inizia un nuovo round! {storyteller.display_name} è il nuovo narratore! Ora descrivi la carta che vuoi giocare con !describe.")

    # Distribuzione carte uniche ai giocatori
    #hands = {}
    for player in players:
        hand = random.sample(deck, cards_per_player) # Rimozione carte dal mazzo man mano che vengono distribuite
        hands[player] = hand
        for card in hand:
            deck.remove(card)

    # Manda le immagini delle carte a ciascun giocatore in privato
    for player, hand in hands.items():
        await player.send(f"Questo è il turno {round_index+1}. Preparati!")
        for card_image in hand:
            file_path = os.path.join(cards_folder, card_image)
            await player.send(file=discord.File(file_path))
        print(f"Turno {round_index+1}.")
        print(f"{player.display_name} ha ricevuto le seguenti carte: {', '.join(hand)}.")

    


# Comando per il narratore per descrivere una carta
@bot.command(name="describe")
async def describe_card(ctx, *, description):
    global storyteller_index, storyteller_described
    storyteller = players[storyteller_index]

    # Controllo se l'autore del comando è il narratore
    if ctx.author != storyteller:
        await ctx.send("Solo il narratore può descrivere una carta.")
        return
    
    if storyteller_described:
        await ctx.send("Il narratore ha già descritto la carta.")
        return

    # Il narratore descrive la carta
    storyteller_described = True
    await ctx.send(f"{storyteller.display_name} ha descritto la sua carta: '{description}'!")
    await ctx.send(f"{storyteller.display_name}, ora invia il numero della carta che vuoi giocare con !choose [numero_carta].")


# Comando per il narratore per scegliere la carta
@bot.command(name="choose")
async def choose_card(ctx, numero_carta: int):
    global storyteller_index, storyteller_card, hands, storyteller_chose
    storyteller = players[storyteller_index]

    # Controllo se l'autore del comando è il narratore
    if ctx.author != storyteller:
        await ctx.send("Solo il narratore può scegliere la carta in questa fase.")
        return
    
    if storyteller_chose:
        await ctx.send("Il narratore ha già scelto la carta.")
        return

    # Verifica che il numero della carta sia valido
    hand = hands[storyteller]
    if numero_carta < 1 or numero_carta > len(hand):
        await ctx.send("Numero di carta non valido. Scegli un numero valido dalla tua mano.")
        return

    # Selezione della carta
    storyteller_chose = True
    storyteller_card = hand.pop(numero_carta - 1)  # Rimuove la carta dalla mano
    played_cards.append((ctx.author, storyteller_card))  # Aggiunge la carta giocata
    await ctx.send(f"{storyteller.display_name} ha scelto una carta segretamente.")

    # A questo punto, gli altri giocatori possono giocare le loro carte
    await ctx.send("Gli altri giocatori ora devono scegliere una carta che si adatta alla descrizione usando !playcard [numero_carta].")


# Comando per i giocatori per scegliere una carta
@bot.command(name="playcard")
async def play_card(ctx, numero_carta: int):
    global storyteller_index, hands, played_cards
    storyteller = players[storyteller_index]

    # Controllo se l'autore del comando è il narratore
    if ctx.author == storyteller:
        await ctx.send("Il narratore non può giocare una carta in questa fase.")
        return
    
    if  not storyteller_described and not storyteller_chose:
        await ctx.send("Il narratore non ha ancora descritto e/o scelto la carta da giocare.")
        return

    # Verifica che il numero della carta sia valido
    hand = hands[ctx.author]
    if numero_carta < 1 or numero_carta > len(hand):
        await ctx.send("Numero di carta non valido. Scegli un numero valido dalla tua mano.")
        return

    # Selezione della carta da parte del giocatore
    carta_scelta = hand.pop(numero_carta - 1)  # Rimuove la carta dalla mano del giocatore
    played_cards.append((ctx.author, carta_scelta))  # Aggiunge la carta giocata
    await ctx.send(f"{ctx.author.display_name} ha giocato una carta.")

    # Controllo se tutti i giocatori (escluso il narratore) hanno giocato una carta
    if len(played_cards) == len(players):
        await show_cards(ctx)

# Funzione per mostrare le carte mescolate
async def show_cards(ctx):
    global played_cards
    # Mescola le carte
    random.shuffle(played_cards)

    # Mostra le carte in ordine casuale senza rivelare chi le ha giocate
    for i, (player, card) in enumerate(played_cards, start=1):
        file_path = os.path.join(cards_folder, card)
        await ctx.send(f"Carta {i}:")
        await ctx.send(file=discord.File(file_path))

    # Informa i giocatori di votare
    await ctx.send("Votate la carta che pensate sia quella del narratore usando !vote [numero_carta].")


# Comando per votare una carta
@bot.command(name="vote")
async def vote_card(ctx, numero_carta: int):
    global storyteller_index, votes, played_cards
    storyteller = players[storyteller_index]

    votes = {i: 0 for i in range(1, len(played_cards) + 1)} # Inizializza i voti per la votazione
    player_votes = {i: [] for i in range(1, len(played_cards) + 1)}  # Tiene traccia dei voti dei giocatori

    # Controllo se l'autore del comando è il narratore
    if ctx.author == storyteller:
        await ctx.send("Il narratore non può votare.")
        return

    # Controllo se il numero della carta votata è valido
    if numero_carta < 1 or numero_carta > len(played_cards):
        await ctx.send("Numero di carta non valido. Scegli un numero valido.")
        return
    
    # # Controllo se il giocatore sta tentando di votare la propria carta
    # if ctx.author == played_cards[numero_carta - 1][0]  # Ottieni il giocatore che ha giocato la carta
    #     await ctx.send("Non puoi votare per la tua carta.")
    #     return

    votes[numero_carta] += 1 # Aggiungi il voto per la carta scelta
    player_votes[numero_carta].append(ctx.author.display_name)  # Aggiungi il nome del giocatore alla lista

    display_votes = []
    for carta, votanti in player_votes.items():  # Itera attraverso le chiavi e i valori del dizionario
        if votanti:  # Se ci sono giocatori che hanno votato per questa carta
            display_votes.append(f"Giocatori che hanno votato per la carta {carta}: {', '.join(votanti)}")
        else:
            display_votes.append(f"Giocatori che hanno votato per la carta {carta}: Nessuno")

    # Controllo se tutti hanno votato
    if sum(votes.values()) == len(players) - 1:
        await ctx.send("\n".join(display_votes))
        await calculate_scores(ctx)


# Funzione per calcolare i punti
async def calculate_scores(ctx):
    global storyteller_card, played_cards, votes, points, storyteller_index, deck, round_index, storyteller_described, storyteller_chose
    storyteller = players[storyteller_index]

    # Trova l'indice della carta del narratore
    storyteller_card_index = next(i for i, (player, card) in enumerate(played_cards, start=1) if player == storyteller)

    # Controlla se tutti o nessuno ha votato la carta del narratore
    if votes[storyteller_card_index] == 0 or votes[storyteller_card_index] == len(players) - 1:
        # Nessuno o tutti hanno votato la carta del narratore
        for player in players:
            if player != storyteller:
                points[player] = points.get(player, 0) + 2  # Ogni altro giocatore guadagna 2 punti
        await ctx.send("Nessuno o tutti hanno votato la carta del narratore. Il narratore ottiene 0 punti, gli altri giocatori guadagnano 2 punti ciascuno.")
    else:
        # Alcuni hanno votato correttamente
        points[storyteller] = points.get(storyteller, 0) + 3  # Il narratore guadagna 3 punti
        for player, card in played_cards:
            if player != storyteller and votes[played_cards.index((player, card)) + 1] > 0:
                points[player] = points.get(player, 0) + 1  # Giocatori che ricevono voti guadagnano 1 punto per voto
        await ctx.send("Il narratore e chi ha votato correttamente guadagnano 3 punti.")

    # Mostra i punteggi finali
    await display_scores(ctx)

    # Check fine partita
    # Verifica se qualcuno ha raggiunto i 30 punti
    for player, score in points.items():
        if score >= 4:
            await ctx.send(f"{player.display_name} ha raggiunto 30 punti e vince la partita!")
            game_started = False
            return  # Termina il gioco
    # Verifica se il mazzo è esaurito
    if len(deck) < cards_per_player*len(players):
        await ctx.send("Il mazzo è esaurito. La partita finisce qui!")
        # Trova il giocatore con più punti
        highest_score = max(points.values())
        winners = [player.display_name for player, score in points.items() if score == highest_score]
        if len(winners) > 1:
            await ctx.send(f"La partita è finita! I vincitori sono: {', '.join(winners)} con {highest_score} punti!")
        else:
            await ctx.send(f"La partita è finita! Il vincitore è {winners[0]} con {highest_score} punti!")
        game_started = False
        return  # Termina il gioco


    # Se la partita non è finita, inizia un nuovo round: ripristina il gioco per il turno successivo
    round_index = round_index+1
    storyteller_card = None
    hands.clear()
    played_cards.clear()
    storyteller_described = False
    storyteller_chose = False
    votes.clear()
    deck = copy.deepcopy(complete_deck)

    await round(ctx)






# Funzione per mostrare i punteggi
async def display_scores(ctx):
    global points
    punteggi = "\n".join([f"{player.display_name}: {points.get(player, 0)} punti" for player in players])
    await ctx.send(f"Punteggi attuali:\n{punteggi}")






# Evento: quando il bot è pronto
@bot.event
async def on_ready():
    print(f'Bot connesso come {bot.user}')

# Setup di gioco
# Comando per iniziare il gioco: risposta a "!startgame"
@bot.command(name="startgame")
async def start_game(ctx):
    global players, game_started
    if game_started:
        await ctx.send("C'è già una partita in corso!")
    else:
        players = []
        game_started = True
        storyteller_index = 0
        await ctx.send("Partita di Dixit iniziata! Usate !join per partecipare e confermate con !begin per chiudere le partecipazioni.")

# Comando per unirsi alla partita: risposta a "!join"
@bot.command(name="join")
async def join_game(ctx):
    if game_started:
        player = ctx.author
        if player not in players:
            players.append(player)
            await ctx.send(f"{player.display_name} si è unito alla partita!")
            print(f"{player.display_name} si è unito alla partita.")
        else:
            await ctx.send(f"{player.display_name} è già nella partita!")
    else:
        await ctx.send("Nessuna partita attiva. Usa !startgame per iniziarne una.")
    #print(players)

# Comando per iniziare ufficialmente la partita: risposta a "begin"
@bot.command(name="begin")
async def begin_game(ctx):
    global game_started
    if not game_started:
        await ctx.send("Nessuna partita attiva. Usa !startgame per iniziarne una.")
    elif len(players) < 0:
        await ctx.send("Servono almeno 3 giocatori per iniziare la partita.")
    else:
        await round(ctx)  # Chiama la funzione per gestire il turno

# Comando per terminare forzatamente la partita
@bot.command(name="endgame")
async def end_game(ctx):
    global game_started
    player = ctx.author
    if not game_started:
        await ctx.send(f"Non c'è nessuna partita da interrompere.")
    else: 
        await ctx.send(f"Partita interrotta da {player.display_name}.")
        game_started = False # La partita è finita, non è più attiva



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
