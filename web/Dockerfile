FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
# Baked into the client bundle at build time. "/v1" is same-origin: the ALB and CloudFront
# both route /v1/* to the API.
ARG NEXT_PUBLIC_API_URL=/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_URL=
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
# Optional same-origin API forwarding for local Compose; AWS routes /v1 at the edge.
ARG PASSIT_API_ORIGIN=
ENV PASSIT_API_ORIGIN=$PASSIT_API_ORIGIN
RUN npm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
