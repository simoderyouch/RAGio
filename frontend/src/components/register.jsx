import { useState } from "react";
import { useForm } from "react-hook-form";
import logo from "../assets/logo.svg";
import useAuthStore from "../stores/authStore";
import { Link } from 'react-router-dom';

const RegisterComponents = () => {
  const registerUser = useAuthStore((state) => state.registerUser);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);
  const { register, handleSubmit, formState: { errors }, watch } = useForm();
  const [showVerificationMessage, setShowVerificationMessage] = useState(false);

  const onSubmit = async (data) => {
    const result = await registerUser(data);
    if (result.status === 200) {
      setShowVerificationMessage(true);
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
           
            {showVerificationMessage ? (
              <div className="text-center text-sm text-gray-700 dark:text-gray-300">
                Merci de vous être inscrit. Veuillez vérifier votre email pour confirmer votre compte.
              </div>
            ) : ( <>
              <h1 className="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
              Créer un compte
            </h1>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 md:space-y-6">
                <div>
                  <label htmlFor="firstName" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                    First Name
                  </label>
                  <input
                    type="text"
                    {...register('first_name', { required: 'First Name is required' })}
                    id="firstName"
                    className={`bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg focus:ring-primary focus:ring-[0.02rem] focus:border-primary block w-full p-2.5  ${errors.first_name ? 'border-red-500' : ''}`}
                    placeholder="First Name"
                  />
                  {errors.first_name && <p className="text-sm mt-1 text-red-500">{errors.first_name.message}</p>}
                </div>
                <div>
                  <label htmlFor="lastName" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                    Last Name
                  </label>
                  <input
                    type="text"
                    {...register('last_name', { required: 'Last Name is required' })}
                    id="lastName"
                    className={`bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg focus:ring-primary focus:ring-[0.02rem] focus:border-primary block w-full p-2.5  ${errors.last_name ? 'border-red-500' : ''}`}
                    placeholder="Last Name"
                  />
                  {errors.last_name && <p className="text-sm mt-1 text-red-500">{errors.last_name.message}</p>}
                </div>
                <div>
                  <label htmlFor="email" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                    Email
                  </label>
                  <input
                    type="text"
                    {...register('email', { required: 'Email is required', pattern: { value: /^\S+@\S+$/i, message: 'Invalid email address' } })}
                    id="email"
                    className={`bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg focus:ring-primary focus:ring-[0.02rem] focus:border-primary block w-full p-2.5  ${errors.email ? 'border-red-500' : ''}`}
                    placeholder="Your Email"
                  />
                  {errors.email && <p className="text-sm mt-1 text-red-500">{errors.email.message}</p>}
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
                <div>
                  <label htmlFor="confirmPassword" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    {...register('confirmPassword', {
                      required: 'Confirm Password is required',
                      validate: value => value === password || 'The passwords do not match'
                    })}
                    id="confirmPassword"
                    className={`bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded-lg focus:ring-primary focus:ring-[0.02rem] focus:border-primary block w-full p-2.5  ${errors.confirmPassword ? 'border-red-500' : ''}`}
                    placeholder="Confirm Password"
                  />
                  {errors.confirmPassword && <p className="text-sm mt-1 text-red-500">{errors.confirmPassword.message}</p>}
                </div>
                <button
                  type="submit"
                  className={`w-full text-white bg-primary focus:ring-4 focus:outline-none focus:ring-primary-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center ${isLoading ? 'opacity-50 cursor-not-allowed' : ''} dark:bg-primary dark:hover:bg-primary dark:focus:ring-primary`}
                  disabled={isLoading}
                >
                  {isLoading ? 'Creating Account...' : 'Create an account'}
                </button>
                {error && <p className="text-sm mt-1 text-red-500">{error}</p>}
                <p className="text-sm font-light text-gray-500 dark:text-gray-400">
                  Vous avez déjà un compte?{' '}
                  <Link to="/user/login" className="font-medium text-primary hover:underline dark:text-primary-500">
                    Connectez-vous ici
                  </Link>
                </p>
              </form>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

export default RegisterComponents;
