FROM node:21
WORKDIR /app
COPY ./app/package.json ./
COPY ./app/package-lock.json ./
RUN npm install
RUN npm install react-router-dom
COPY ./app .
EXPOSE 3000
CMD ["npm", "start"]