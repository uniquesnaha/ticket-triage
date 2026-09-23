# Local development image (hot reload via docker compose). Production builds are
# served by Vercel directly from `npm run build`.
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
