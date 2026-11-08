# Shop-Now.net Instagram daily post agent

Posts one product card a day to @shopnow_net at 8:00 AM local time (default time zone Asia/Kabul; set the repository variable POST_TZ to change it).
The 12 product cards (Rice, Flour, Sugar, Salt, Olive Oil, Cooking Oil, Almonds, Pistachios, Raisins, Hand Soap, Notebooks, Pens) are drawn by `cards.py` (free, no AI service) and posted in rotation by `post_instagram.py`. Every caption ends with the Shop-Now.net signature. No offers, prices or delivery promises are used.

This repository is public only because Instagram must download each image from a public link. It contains no secrets: the Composio API key lives in Settings > Secrets and variables > Actions.

Required: secret `COMPOSIO_API_KEY`; variable `IG_CONNECTED_ACCOUNT_ID`.
Run the workflow manually with mode `check` (tests the connection, posts nothing) or `dry_run` (shows the next post, posts nothing).
