# LightHouse: AI WhatsApp Bot for Domestic Workers

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add other badges later e.g., build status -->

Accessible Financial & Employment Tools for Domestic Workers on WhatsApp, powered by AI and integrated with Sampatti Card. Developed as part of the Code for GovTech (C4GT) initiative.

**Project Repository:** [Lighthouse-chatbot](https://github.com/avinashg0y4l/lighthouse-chatbot/) 

## Table of Contents

*   [Problem Statement](#problem-statement)
*   [Solution: LightHouse Chatbot](#solution-lighthouse-chatbot)
*   [Features](#features)
*   [Technology Stack](#technology-stack)
*   [Architecture Overview](#architecture-overview)
*   [Setup and Installation](#setup-and-installation)
*   [Running the Application](#running-the-application)
*   [Usage](#usage)
*   [Testing](#testing)
*   [Project Milestones](#project-milestones)
*   [Contributing](#contributing)
*   [License](#license)
*   [Acknowledgements](#acknowledgements)

## Problem Statement

Domestic workers often face significant barriers in accessing formal financial services and managing employment records. Communication typically relies on WhatsApp, frequently using voice messages due to varying literacy levels. LightHouse aims to bridge this gap by providing an accessible digital tool within their familiar communication platform, promoting financial inclusion and streamlining employment management through integration with the Sampatti Card ID system.

## Solution: LightHouse Chatbot

LightHouse is an open-source, AI-powered WhatsApp chatbot designed for domestic workers and employers. It offers:

*   **Accessibility:** Operates entirely within WhatsApp.
*   **Multimodal Input:** Supports both **text and voice** commands.
*   **Bilingual:** Understands and interacts in **Hindi and English**.
*   **Integration:** Securely links user interactions to their **Sampatti Card ID**.
*   **Core Services:** Provides intuitive access to Digital KYC, Attendance Tracking, and Salary Management.

## Features

**Implemented:**

*   **User Registration:** Onboard Workers/Employers via WhatsApp, linking to Sampatti Card ID (`register <ID> <role>`).
*   **Attendance Logging:** Workers can log check-in/checkout times (`checkin`, `checkout`).
*   **Salary Logging:** Employers can record salary payments (`log salary <WorkerID> <Amt> [Date]`).
*   **Salary Inquiry:** Workers can query their recent salary history (`salary`).
*   **Basic KYC Upload:** Workers can upload Image/PDF documents via WhatsApp media; files are received and saved (currently locally), DB record created.
*   **Voice & Text Input:** Core commands processed via Google Dialogflow ES NLP for both modalities.
*   **Bilingual NLP:** Dialogflow agent trained for basic Hindi and English understanding.

**Planned Enhancements:**

*   Full Hindi language support (responses & language switching).
*   Refined KYC workflow (document type specification, status tracking, admin verification).
*   Secure cloud storage (S3/GCS) for KYC documents.
*   Employment verification command.
*   Notifications and reminders (requires template approval).
*   Admin monitoring dashboard/logging.
*   Database migrations.
*   Comprehensive unit and integration tests.

## Technology Stack

*   **Backend:** Python 3.10+, Flask, Flask-SQLAlchemy
*   **Database:** PostgreSQL 15+
*   **NLP:** Google Cloud Dialogflow ES
*   **WhatsApp Integration:** Twilio API for WhatsApp
*   **Containerization:** Docker, Docker Compose
*   **Libraries:** google-cloud-dialogflow, twilio, requests, psycopg2-binary, python-dotenv
*   **Local Tunneling:** ngrok

## Architecture Overview

(High Level Flow)

`User (WhatsApp)` <-> `Twilio API` <-> `ngrok` <-> `Flask Backend (Docker)` <-> `Dialogflow ES API`
                                                         |
                                                         v
                                             `PostgreSQL DB (Docker)`
                                                         |
                                                         v
                                             `File Storage (Local/Cloud)`

*(A more detailed diagram could be added later)*

## Setup and Installation

**Prerequisites:**

*   Git
*   Python 3.10+ and Pip
*   Docker & Docker Compose
*   `ngrok` account and executable
*   Twilio Account (with SID, Auth Token, and a WhatsApp Sandbox or activated number)
*   Google Cloud Platform Project with Dialogflow API enabled
*   Dialogflow ES Agent created (see below)
*   Dialogflow Service Account JSON Key file

**Steps:**

1.  **Clone Repository:**
    ```bash
    git clone [Link to your LightHouse GitHub Repo] # Replace with your repo link
    cd lighthouse-chatbot
    ```

2.  **Set up Dialogflow ES Agent:**
    *   Create a Dialogflow ES Agent linked to your GCP project.
    *   Enable both **English (`en`)** and **Hindi (`hi`)** languages.
    *   Create **Entities:**
        *   `@role` (Entries: `worker`, `employer` with EN/HI synonyms; Regexp/Auto-expand OFF)
        *   `@sampatti_id` (Use **Regexp entity** with the correct pattern, e.g., `^[A-Z]{3}\d{5}$)
    *   Create **Intents** (mixing EN/HI training phrases, annotating params, setting required/prompts where needed):
        *   `RegisterUser` (Params: `@sampatti_id`, `@role` - both REQUIRED)
        *   `CheckIn`
        *   `CheckOut`
        *   `SalaryInquiry`
        *   `LogSalary` (Params: `@sampatti_id`, `@sys.number` (rename to `amount`), `@sys.date` - ID & amount REQUIRED)
        *   `Default Welcome Intent`
        *   `Default Fallback Intent`
    *   **Train** the agent.
    *   Create a **Service Account** in GCP IAM with the "Dialogflow API Client" role.
    *   Download the **JSON key file** for this service account.

3.  **Configure Environment Variables:**
    *   Copy the downloaded Dialogflow JSON key file into the project root directory and name it `dialogflow_key.json`.
    *   Create a file named `.env` in the project root directory by copying `.env.example` (if you create one) or by creating it manually.
    *   **Edit `.env` and replace placeholders** with your actual credentials:
        ```dotenv
        # .env
        POSTGRES_USER=lighthouse_user
        POSTGRES_PASSWORD=YourChosen_DB_Password # Choose a strong password
        POSTGRES_DB=lighthouse_db
        DATABASE_URL=postgresql://lighthouse_user:YourChosen_DB_Password@db:5432/lighthouse_db # Use SAME password

        TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxx
        TWILIO_AUTH_TOKEN=your_twilio_auth_token
        TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886 # Or your purchased number

        FLASK_CONFIG=development
        FLASK_DEBUG=1 # Set to 0 in production
        SECRET_KEY=your_strong_random_secret_key # Generate one!

        DIALOGFLOW_PROJECT_ID=your-gcp-project-id # e.g., lighthouseagent-gogx
        GOOGLE_APPLICATION_CREDENTIALS=/app/dialogflow_key.json # Path inside container
        ```
    *   Make sure `dialogflow_key.json` and `.env` are listed in your `.gitignore` file!

4.  **Build and Run Containers:**
    ```bash
    docker compose up --build -d
    ```

5.  **Initialize Database Tables:** Run the Flask CLI command via Docker Compose:
    ```bash
    docker compose exec app flask create-db
    ```

6.  **Start ngrok:** Open a *new terminal* and expose the Flask app's port (default 5000):
    ```bash
    ngrok http 5000
    ```
    Note the `https://....ngrok-free.app` URL provided.

7.  **Configure Twilio Webhook:**
    *   Go to your Twilio Console -> Messaging -> Try it out -> Send a WhatsApp message -> Sandbox Settings.
    *   In the "WHEN A MESSAGE COMES IN" field, paste your **ngrok HTTPS URL** and append `/webhook/whatsapp`. (e.g., `https://your-id.ngrok-free.app/webhook/whatsapp`)
    *   Ensure the method is set to `HTTP POST`.
    *   Save the configuration.
    *   If using the Sandbox, ensure your test phone number is connected by sending the `join <keyword>` message to the Sandbox number.

## Running the Application

*   **Start:** `docker compose up -d`
*   **Stop:** `docker compose down`
*   **View Logs:** `docker compose logs -f app` (Follows logs from the Flask app container)
*   **Restart App:** `docker compose restart app`

## Usage

Interact with the bot via your connected WhatsApp number:

*   **Register (Worker):** `register <YourSampattiID> worker` (e.g., `register ABC12345 worker`)
*   **Register (Employer):** `register <YourSampattiID> employer` (e.g., `register EMP98765 employer`)
*   **Check In (Worker):** `checkin`
*   **Check Out (Worker):** `checkout`
*   **Log Salary (Employer):** `log salary <WorkerID> <Amount> [YYYY-MM-DD]` (e.g., `log salary ABC12345 500 2025-05-01`, or `log salary ABC12345 600`)
*   **Check Salary (Worker):** `salary`
*   **Upload KYC Document (Worker):** Send an Image or PDF file directly as an attachment.
*   **Voice Input:** Send a voice message containing one of the above commands (e.g., record yourself saying "check in").

*(Add more commands as they are implemented, like help, language switching, kyc status etc.)*

## Testing

Currently, testing is primarily done manually via WhatsApp interactions and by observing application logs (`docker compose logs -f app`).

**Planned Testing Strategy:**

*   **Unit Tests:** Using `pytest` to test individual functions in `commands.py`, `nlp.py`, etc. (mocking external dependencies like DB and APIs).
*   **Integration Tests:** Testing interactions between components (e.g., webhook receiving data -> command handler -> database update).
*   **End-to-End Tests:** Simulating full user journeys via mock WhatsApp sessions if possible, or structured manual testing plans.

*(Add specific commands to run tests once implemented, e.g., `docker compose exec app pytest`)*

## Project Milestones

*(You can paste the Milestone breakdown from the proposal here or link to it)*

1.  **Milestone 1 (Weeks 1-6):** Foundation, Core Text Features & Mid-Point Goal (Completed basic text features)
2.  **Milestone 2 (Weeks 7-11):** NLP Integration (Voice & Multilingual) & Refinements (In Progress)
3.  **Milestone 3 (Weeks 12-14):** Security, Scalability, Admin & Release Prep

## Contributing

Contributions are welcome! Please follow standard open-source practices:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (`git checkout -b feature/your-feature-name`).
3.  Make your changes and commit them with clear messages.
4.  Push your branch to your fork (`git push origin feature/your-feature-name`).
5.  Create a Pull Request back to the main repository's `main` branch.

Please refer to the `CONTRIBUTING.md` file (to be created) for more detailed guidelines and coding standards. Report bugs or suggest features using the GitHub Issues tab.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details. *(You will need to create a file named `LICENSE` in the root and paste the MIT License text into it)*.

## Acknowledgements

*   This project is developed as part of the **Code for GovTech (C4GT)** program.
*   In collaboration with **Sampatti Card**.
*   Guidance from assigned Mentors (TBD).

---

