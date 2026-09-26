# RadioTrace

Initial full-stack structure for a Flask API, React + TypeScript frontend, and MongoDB database.

## Services

- `frontend/radiotrace`: Vite React frontend served by Nginx on port `8080`
- `backend`: Flask API served by Gunicorn on port `5050`
- `mongo`: MongoDB on port `27017`, with data stored in a Docker volume

## Run with Docker

```sh
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8080`. The API health endpoint is available at `http://localhost:5050/api/health`.

## Run the frontend locally

```sh
cd frontend/radiotrace
npm install
npm run dev
```

Vite proxies requests from `/api` to the backend at `http://localhost:5050`.