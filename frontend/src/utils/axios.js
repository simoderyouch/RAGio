import axios from 'axios';
export const BASE_URL = process.env.REACT_APP_API_URL;

export default axios.create({
    baseURL: BASE_URL,
    withCredentials: true
});

export const axiosPrivate = axios.create({
    baseURL: BASE_URL,
    withCredentials: true
});