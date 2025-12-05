import { useState, useEffect, useCallback } from 'react';
import useAxiosPrivate from './useAxiosPrivate';

const useFetch = (url) => {
  const axiosInstance = useAxiosPrivate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axiosInstance.get(url);
      setData(response.data);
    } catch (err) {
      setError(err);
      setData(null);
      // Re-throw for components that need to handle errors
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [axiosInstance, url]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, error, isLoading, fetchData };
};

export default useFetch;

