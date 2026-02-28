name: YouTube Channel 3 - Psychological Talks

on:
  schedule:
    # 6:30 PM IST (1:00 PM UTC)
    - cron: "0 13 * * *"

    # 11:30 PM IST (6:00 PM UTC)
    - cron: "0 18 * * *"

  workflow_dispatch:

jobs:
  upload:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install --upgrade pip
          pip install google-api-python-client
          pip install google-auth
          pip install google-auth-oauthlib
          pip install google-auth-httplib2

      - name: Run Psychological Channel Upload
        env:
          # ======================
          # DRIVE
          # ======================
          SERVICE_ACCOUNT_JSON: ${{ secrets.SERVICE_ACCOUNT_JSON }}
          FOLDER_ID_CH3: ${{ secrets.FOLDER_ID_CH3 }}
          UPLOADED_FOLDER_ID_CH3: ${{ secrets.UPLOADED_FOLDER_ID_CH3 }}

          # ======================
          # YOUTUBE (CHANNEL 3)
          # ======================
          YT_CLIENT_ID_CH3: ${{ secrets.YT_CLIENT_ID_CH3 }}
          YT_CLIENT_SECRET_CH3: ${{ secrets.YT_CLIENT_SECRET_CH3 }}
          YT_REFRESH_TOKEN_CH3: ${{ secrets.YT_REFRESH_TOKEN_CH3 }}

        run: python Aesthetic.py
