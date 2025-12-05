import  { useState } from "react";
import { useForm } from "react-hook-form";
import useAuthStore from "../stores/authStore";
import { Link , useNavigate   } from 'react-router-dom';
import logo from "../assets/logo.svg";

const  Login = () => {
  const loginUser = useAuthStore((state) => state.loginUser);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);
    const { register, handleSubmit, formState: { errors }, watch } = useForm();
    const navigateTo = useNavigate()
  
    const onSubmit = async (data) => {
    try {
     const res =  await loginUser(data);
      if (res.status = 200) {
        navigateTo('/chatroom')
      }
    } catch (error) {
      // Error logging user
    } 
  };
  
  const password = watch("password");

  return (
    <section className="backgroud-landing min-h-[100vh] py-[4rem]">
      <div className="flex flex-col items-center justify-center px-6 py-8 mx-auto lg:py-0">
        <a href="/" className="flex items-center mb-6 text-2xl font-semibold text-gray-900 dark:text-white">
          <img className="!w-[12rem]" src={logo} alt="Logo" />
        </a>
        <div className="w-full bg-white rounded-lg shadow dark:border md:mt-0 sm:max-w-md xl:p-0 dark:bg-gray-800 dark:border-gray-700">
          <div className="p-6 space-y-4 md:space-y-6 sm:p-8">
            <h1 className="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
            Connectez-vous à votre compte
            </h1>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 md:space-y-6">
              <div>
                <label htmlFor="firstName" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                  Email ou UserName
                </label>
                <input
                  type="text"
                  {...register('username_or_email', { required: 'Email ou UserName is required' })}
                  id="username_or_email"
                  className={`bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg focus:ring-primary focus:ring-[0.02rem] focus:border-primary block w-full p-2.5  ${errors.firstName ? 'border-red-500' : ''}`}
                  placeholder="Email ou UserName"
                />
                {errors.username_or_email && <p className="text-sm mt-1 text-red-500">{errors.username_or_email.message}</p>}
              </div>
              
              <div>
                <label htmlFor="password" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                  Password
                </label>
                <input
                  type="password"
                  {...register('password', { required: 'Password is required', minLength: { value: 8, message: 'Password must be at least 8 characters long' } })}
                  id="password"
                  className={`bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg focus:ring-primary focus:ring-[0.02rem] focus:border-primary block w-full p-2.5  ${errors.password ? 'border-red-500' : ''}`}
                  placeholder="Password"
                />
                {errors.password && <p className="text-sm mt-1 text-red-500">{errors.password.message}</p>}
              </div>
              
              <button
                type="submit"
                className={`w-full text-white bg-primary focus:ring-4 focus:outline-none focus:ring-primary-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center ${isLoading ? 'opacity-50 cursor-not-allowed' : ''} dark:bg-primary dark:hover:bg-primary dark:focus:ring-primary`}
                disabled={isLoading}
              >
                {isLoading ? 'Connecting...' : 'Connecter'}
              </button>
              
              {error && <p className="text-sm mt-1 text-red-500">{error}</p>}
              <p className="text-sm font-light text-gray-500 dark:text-gray-400">
              Nouvel utilisateur?{' '}
              <Link to="/user/register" className="font-medium text-primary hover:underline dark:text-primary-500">
                Registre
                </Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Login;
