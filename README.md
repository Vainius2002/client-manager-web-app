# 🗂️ Client Manager Web App

This is a full-stack **Client Management System** built with **Flask**, **Flask-SocketIO**, **PostgreSQL**, and **AWS S3** for image storage. It allows users to create and manage client profiles, including uploading and managing multiple images per client.

> 🔐 Default login:  
> **Username:** `admin`  
> **Password:** `123`

---

## 🌐 Features

- ✅ Create new clients with detailed info:
  - `vardas` (first name)
  - `pavarde` (last name)
  - `imone` (company)
  - `adresas` (address)
  - `pastabos` (notes)
- 🖼️ Upload **multiple images** per client.
- ✏️ Edit any client's information and replace or delete images.
- 🗑️ Delete client records entirely.
- 🔍 Search for clients by name or details.
- ☁️ Cloud-based storage using:
  - **AWS S3** for storing images.
  - **PostgreSQL** for storing data.

---

## 🚀 Deployment (Render / Cloud)

You can deploy this app to **Render** or any similar cloud provider.

### 🔧 Environment Variables

Set the following environment variables either:
- in a `.env` file for local development
- or in your Render Dashboard → Environment tab

```env
AWS_ACCESS_KEY_ID=your_key_id
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region
BUCKET_NAME=your_s3_bucket_name
DATABASE_URL=your_postgresql_database_url
```

---

## 💻 Local Development

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/client-manager.git
cd client-manager
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up `.env`

Create a `.env` file in the root folder:

```env
AWS_ACCESS_KEY_ID=your_key_id
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region
BUCKET_NAME=your_bucket_name
DATABASE_URL=your_postgres_url
```

### 4. Run the server

```bash
python app.py
```

Then open your browser at `http://localhost:5000`

---

## 🧰 Tech Stack

- **Backend:** Flask + Flask-SocketIO
- **Database:** PostgreSQL
- **File Storage:** AWS S3
- **Hosting:** Render.com (used in this project)

---

## 📬 Contact

Built by Vainius Lunys.  
Deployed on [Render](https://render.com).

---
