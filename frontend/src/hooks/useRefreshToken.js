import axios from "../utils/axios";
import useAuthStore from "../stores/authStore";
import { useNavigate } from "react-router-dom";

 export const useRefreshToken = () =>  {
    const setToken = useAuthStore((state) => state.setToken)
    const navigateTo = useNavigate()
     const refresh = async () => {
      try {
      
        const response = await axios.get('/api/auth/token_refresh/', {
          withCredentials: true
          
      }); 
      
      setToken(response.data.access_token )
      let user = JSON.parse(localStorage.getItem('user'));
user.access_token = response.data.access_token;
localStorage.setItem('user', JSON.stringify(user));


       return response.data.access_token 
      } catch (error) {
        if (error.response && error.response.status === 401) {
          navigateTo('/user/login', {replace:true})
        }
      }
     }
    
   

    return refresh
};

