docker run --name my-pgvector \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=vectordb \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16