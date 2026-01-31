FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 7860

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "7860"]
