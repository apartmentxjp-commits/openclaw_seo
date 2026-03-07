import { TwitterApi } from 'twitter-api-v2';

const client = new TwitterApi({
    clientId: process.env.X_CLIENT_ID || '',
    clientSecret: process.env.X_CLIENT_SECRET || '',
});

export const twitterClient = client.readWrite;
export const twitterAuth = client;
