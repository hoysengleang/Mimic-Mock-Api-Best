# syntax=docker/dockerfile:1

# --- Development ------------------------------------------------------------
# Vite dev server with hot reload. Source is bind-mounted by docker-compose.
FROM node:20-alpine AS dev

WORKDIR /app
ENV CI=1

RUN corepack enable

# Manifests first so the install layer caches independently of source changes.
COPY package.json yarn.lock .yarnrc.yml ./
RUN yarn install --immutable || yarn install

COPY . .

EXPOSE 5173
CMD ["yarn", "dev", "--host"]


# --- Build ------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app
RUN corepack enable

COPY package.json yarn.lock .yarnrc.yml ./
RUN yarn install --immutable || yarn install

COPY . .
RUN yarn build


# --- Production -------------------------------------------------------------
# Static files served by nginx, which also proxies /api and /mock to the
# backend so the browser only ever talks to one origin.
FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
