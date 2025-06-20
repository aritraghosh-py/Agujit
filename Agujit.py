from telethon import events, TelegramClient
import os
import asyncio
import time

# Telegram API credentials
api_id = 25974406
api_hash = 'c9f0ebfb853736227f3ef6d799b39305'
guessSolver = TelegramClient('session_name', api_id, api_hash)
chatid = -4754942649  # Change this to your group/channel ID

from telethon.tl.types import PhotoStrippedSize

# Variables to track response and retries
last_guess_time = 0
guess_timeout = 3  # Time to wait for a response after /guess
pending_guess = False  # Track if waiting for a response
retry_lock = asyncio.Lock()  # Prevent concurrent retries

# Function to handle non-stop guessing
@guessSolver.on(events.NewMessage(from_users=1891133819, pattern=".bin", outgoing=True))
async def start_guessing(event):
    print("Non-stop guessing started.")
    while True:
        try:
            await send_guess_command()
            await asyncio.sleep(3)  # Wait before sending another /guess
        except Exception as e:
            print(f"Error in sending /guess: {e}")
            await asyncio.sleep(3)

# Send /guess command and track the time
async def send_guess_command():
    global last_guess_time, pending_guess
    try:
        await guessSolver.send_message(entity=chatid, message='/guess')
        print("Sent /guess command.")
        last_guess_time = time.time()
        pending_guess = True  # Mark as awaiting response
    except Exception as e:
        print(f"Error in sending /guess: {e}")

# Detect "Who's that Pokémon?" game logic and respond
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="Who's that pokemon?", chats=(int(chatid)), incoming=True))
async def guess_pokemon(event):
    global last_guess_time, pending_guess
    try:
        pending_guess = False  # Reset pending status on valid response
        for size in event.message.photo.sizes:
            if isinstance(size, PhotoStrippedSize):
                size = str(size)
                for file in os.listdir("cache/"):
                    with open(f"cache/{file}", 'r') as f:
                        file_content = f.read()
                    if file_content == size:
                        Msg = file.split(".txt")[0]
                        await asyncio.sleep(1)
                        await guessSolver.send_message(chatid, Msg)
                        last_guess_time = time.time()
                        await asyncio.sleep(3)
                        await send_guess_command()
                        return
                # Cache the size for new Pokémon
                with open("saitama/cache.txt", 'w') as file:
                    file.write(size)
    except Exception as e:
        print(f"Error in guessing Pokémon: {e}")

# Save Pokémon data when the game reveals the answer
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="The pokemon was ", chats=int(chatid)))
async def save_pokemon(event):
    global last_guess_time, pending_guess
    try:
        pending_guess = False  # Reset pending status on valid response
        pokemon_name = ((event.message.text).split("The pokemon was **")[1]).split("**")[0]
        with open(f"cache/{pokemon_name}.txt", 'w') as file:
            with open("saitama/cache.txt", 'r') as inf:
                cont = inf.read()
                file.write(cont)
        os.remove("saitama/cache.txt")
        await send_guess_command()
    except Exception as e:
        print(f"Error in saving Pokémon data: {e}")

# Handle "There is already a guessing game being played" message
@guessSolver.on(events.NewMessage(from_users=572621020, pattern="There is already a guessing game being played", chats=int(chatid)))
async def handle_active_game(event):
    print("A guessing game is already active. Retrying shortly...")
    await asyncio.sleep(10)  # Wait 10 seconds before retrying
    await send_guess_command()

# Function to monitor bot behavior and retry if no response
async def monitor_responses():
    global last_guess_time, pending_guess
    while True:
        try:
            async with retry_lock:  # Prevent multiple retries
                # Retry if no response within the timeout period
                if pending_guess and (time.time() - last_guess_time > guess_timeout):
                    print("No response detected after /guess. Retrying...")
                    await send_guess_command()
            await asyncio.sleep(3)  # Check every 6 seconds
        except Exception as e:
            print(f"Error in monitoring responses: {e}")
            await asyncio.sleep(6)

# Reconnection logic
async def ensure_connection():
    while True:
        try:
            if not guessSolver.is_connected():
                print("Reconnecting...")
                await guessSolver.connect()
            if not guessSolver.is_user_authorized():
                print("Session expired. Please log in again.")
                break
            await asyncio.sleep(5)  # Check connection every 5 seconds
        except Exception as e:
            print(f"Error during reconnection: {e}")
            await asyncio.sleep(5)

# Main bot loop
async def main():
    await guessSolver.start()
    print("Bot started.")
    await asyncio.gather(
        ensure_connection(),  # Ensure the bot stays connected
        monitor_responses(),  # Monitor responses and handle retries
        guessSolver.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())
