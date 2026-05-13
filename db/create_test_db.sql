-- Executar uma única vez como superusuário para criar o banco de testes.
-- psql -U postgres -h localhost -p 5434 -f db/create_test_db.sql

CREATE DATABASE churn_test OWNER churn_user;
