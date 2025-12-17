# Dockerfile - SIMPLE VERSION
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production
RUN npm install @iamtraction/google-translate

COPY . .

RUN mkdir -p downloads logs

CMD ["node", "copier.js"]