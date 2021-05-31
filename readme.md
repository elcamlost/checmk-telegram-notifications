# What is this? #

This is a checkmk notification plugin to allow sending notifications via Telegram bot. It supports sending plain text as well as graphs.

# Setup #

- Create a Telegram Bot using [BotFather](https://core.telegram.org/bots#6-botfather) and store the bot token
- Either:
  - Create a new telegram group and invite your new bot (look for it using `@Username` where Username is the value you entered at BotFather)
  - Directly write your bot
- Send at least one message
- Get the chat ID of the chat by running
  ```
  BOT_TOKEN="<YOUR BOT TOKEN HERE>"
  curl -svk https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=0 | grep "chat" -A 5 | grep 'id'
  ```
- Run the packaging script to create a checkmk package
- Install the package on the checkmk host
- Configure a notification rule where you set at least your chat ID and bot token
