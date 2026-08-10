# Tarpon — Control Plane UI

Dashboard administrativo da plataforma **Tarpon**: controle de modelos champion/challenger, gerenciamento multi-tenant, monitoramento de inferências e visão executiva de negócio.

---

## Visão geral

| Camada | Tecnologia |
|---|---|
| Framework | React 18 + TypeScript |
| Bundler | Vite 6 |
| Roteamento | React Router v6 |
| Estado global | Zustand v5 (persist) |
| Server state | TanStack Query v5 |
| HTTP | Axios |
| UI primitivos | Radix UI + design tokens OKLCH |
| Estilização | Tailwind CSS v3 + CSS custom properties |
| Runtime alvo | Node ≥ 20 / npm ≥ 11.10.0 |

---

## Pré-requisitos

```
Node.js  >= 20.x
npm      >= 11.10.0   (verifique com: npm -v)
```

> **Por que npm ≥ 11.10?**  
> O projeto usa `min-release-age=7` no `.npmrc`, que exige npm 11.10.0 ou superior.  
> Com versões anteriores essa política não é aplicada. Veja [Segurança de dependências](#segurança-de-dependências).

---

## Início rápido

```bash
# 1. Entre no diretório do frontend
cd frontend

# 2. Instale as dependências (use npm ci — não npm install)
npm ci

# 3. Copie as variáveis de ambiente
cp .env.example .env.local
# Edite .env.local com a URL da API e chaves necessárias

# 4. Suba o servidor de desenvolvimento
npm run dev
# → http://localhost:5173
```

> O backend FastAPI deve estar rodando em `http://localhost:8000`.  
> O Vite faz proxy automático: chamadas para `/api/*` são repassadas ao backend.

---

## Scripts

| Comando | Descrição |
|---|---|
| `npm run dev` | Servidor de desenvolvimento com HMR |
| `npm run build` | Type-check + build de produção em `dist/` |
| `npm run preview` | Serve o build de produção localmente |
| `npm run lint` | ESLint em todos os arquivos `.ts` / `.tsx` |

---

## Variáveis de ambiente

Crie um arquivo `.env.local` na raiz do diretório `frontend/`:

```env
# URL base da API FastAPI (sem trailing slash)
VITE_API_BASE_URL=http://localhost:8000

# URL base do serviço de inferência (pode ser o mesmo)
VITE_INFERENCE_BASE_URL=http://localhost:8000
```

> Todas as variáveis expostas ao browser devem começar com `VITE_`.  
> Nunca coloque segredos (JWT secret, API keys reais) em variáveis `VITE_`.

---

## Estrutura de diretórios

```
frontend/
├── public/                  ← assets estáticos
├── src/
│   ├── components/
│   │   ├── layout/          ← AppLayout, Sidebar, TenantSelector, Topbar
│   │   ├── models/          ← ConfigureModelDialog, PromoteDialog, DeactivateDialog
│   │   ├── predictions/     ← PredictionTable
│   │   └── primitives/      ← design system: MetricCard, Sparkline, Donut, Table…
│   ├── hooks/               ← useModels, usePredictions, useApiKeys, useTenants
│   ├── pages/               ← uma página por rota
│   ├── services/            ← clientes HTTP (apiClient, inferenceClient)
│   ├── store/               ← authStore (Zustand + persist)
│   ├── types/               ← interfaces TypeScript dos schemas da API
│   ├── App.tsx              ← roteamento principal
│   ├── main.tsx             ← entry point
│   └── index.css            ← tokens de design OKLCH + classes utilitárias
├── .npmrc                   ← min-release-age=7
├── package.json
├── vite.config.ts           ← proxy /api → backend
├── tailwind.config.ts
└── tsconfig.json
```

---

## Segurança de dependências

Para reduzir riscos de ataques de supply chain, o projeto adota duas práticas no npm.

### `npm ci`

Use **`npm ci`** em vez de `npm install` em todos os ambientes — desenvolvimento limpo, CI/CD e produção.

O `npm ci` instala exatamente as versões registradas no `package-lock.json`. Isso torna o build previsível e evita que ranges como `^1.2.3` alterem silenciosamente o resultado da instalação sem revisão.

```bash
# ✅ correto
npm ci

# ⚠️ evitar em CI e produção
npm install
```

### `min-release-age=7`

O arquivo `.npmrc` define:

```ini
min-release-age=7
```

Essa configuração instrui o npm a instalar apenas versões de pacotes publicadas há **mais de 7 dias**. Isso reduz a exposição a pacotes recém-publicados que possam ter sido comprometidos antes de serem detectados pela comunidade ou removidos do registro — um vetor comum em ataques de curta duração.

> **Requisito:** `min-release-age` exige **npm ≥ 11.10.0**.  
> Por isso o projeto declara no `package.json`:
>
> ```json
> {
>   "packageManager": "npm@11.12.1",
>   "engines": {
>     "node": ">=20",
>     "npm": ">=11.10.0"
>   }
> }
> ```
>
> Com npm antigo, a política não é aplicada. Verifique com `npm -v`.

---

## Build de produção

```bash
npm ci
npm run build
# Artefatos em: frontend/dist/
```

O diretório `dist/` pode ser servido por qualquer servidor de arquivos estáticos (Nginx, Caddy, S3 + CloudFront, etc.).

Exemplo com Nginx:

```nginx
server {
    listen 80;
    root /var/www/helix-ui/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/;
    }
}
```

---

## Lint e qualidade

```bash
npm run lint
```

O ESLint está configurado com regras TypeScript recomendadas. Para habilitar verificação de tipos completa (recomendado em produção), edite `eslint.config.js`:

```js
// substitua tseslint.configs.recommended por:
tseslint.configs.recommendedTypeChecked
```

---

## Licença

Uso interno — não distribuir. Veja `LICENSE` na raiz do repositório.
