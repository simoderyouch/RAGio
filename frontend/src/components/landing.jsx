import { GoArrowRight, GoUpload, GoFileDirectory, GoComment, GoShield } from "react-icons/go";
import { HiOutlineDocumentText, HiOutlineSparkles, HiOutlineLightningBolt } from "react-icons/hi";
import useFileStore from '../stores/fileStore';
import useAuthStore from '../stores/authStore';
import { Link, useNavigate } from 'react-router-dom';
import NavBar from "./shared/navBar.jsx";
import Loading from "./ui/Loading.jsx";
import { useState, useEffect } from 'react';
import useAxiosPrivate from "../hooks/useAxiosPrivate";

const Landing = () => {
  const handleUpload = useFileStore((state) => state.handleUpload);
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const navigate = useNavigate();
  const axiosInstance = useAxiosPrivate();

  // File conversion utilities
  const fileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = (error) => reject(error);
    });
  };

  const base64ToFile = (base64, filename) => {
    const arr = base64.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  };

  // Handle pending file upload after login
  useEffect(() => {
    const fetchData = async () => {
      const storedFile = localStorage.getItem('pendingFile');
      if (storedFile && token && user) {
        setIsUploading(true);
        try {
          const { base64, name } = JSON.parse(storedFile);
          const file = base64ToFile(base64, name);
          const res = await handleUpload(file, axiosInstance);
          setIsUploading(false);
          navigate(`/chatroom`);
          localStorage.removeItem('pendingFile');
        } catch (error) {
          setIsUploading(false);
        }
      }
    };
    fetchData();
  }, [token, user, handleUpload]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) processFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const processFile = async (file) => {
    if (token && user) {
      setIsUploading(true);
      const res = await handleUpload(file, axiosInstance);
      setIsUploading(false);
      navigate(`/chatroom/${res.data.file.id}`);
    } else {
      const base64File = await fileToBase64(file);
      localStorage.setItem('pendingFile', JSON.stringify({ base64: base64File, name: file.name }));
      navigate('/user/login');
    }
  };

  const features = [
    {
      icon: <HiOutlineDocumentText className="w-6 h-6" />,
      title: "Multi-formats",
      description: "PDF, TXT, CSV et Markdown (MD) supportés"
    },
    {
      icon: <HiOutlineSparkles className="w-6 h-6" />,
      title: "IA Avancée",
      description: "Analyse intelligente avec NLP de pointe"
    },
    {
      icon: <HiOutlineLightningBolt className="w-6 h-6" />,
      title: "Réponses Rapides",
      description: "Obtenez des réponses précises instantanément"
    },
    {
      icon: <GoShield className="w-6 h-6" />,
      title: "Sécurisé",
      description: "Vos documents restent privés et protégés"
    }
  ];

  const fileTypes = [
    { name: "PDF", color: "bg-red-500" },
    { name: "TXT", color: "bg-slate-500" },
    { name: "CSV", color: "bg-amber-500" },
    { name: "MD", color: "bg-purple-500" }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-rose-50 relative overflow-hidden">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -left-40 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 right-1/3 w-72 h-72 bg-primary/5 rounded-full blur-3xl" />
        {/* Grid pattern */}
        <div 
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60' viewBox='0 0 60 60'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23711037' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
          }}
        />
      </div>

      <NavBar />

      {/* Hero Section */}
      <main className="relative">
        <div className="container max-w-6xl mx-auto px-6 pt-16 pb-24">
          {/* Hero Content */}
          <div className="text-center mb-16 animate-fade-in">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-full text-sm font-medium mb-8 border border-primary/20">
              <HiOutlineSparkles className="w-4 h-4" />
              <span>Propulsé par l'Intelligence Artificielle</span>
            </div>

            {/* Main Heading */}
            <h1 className="font-bold text-5xl md:text-6xl lg:text-7xl leading-[3.3rem] tracking-tighter mb-6 text-slate-900">
              <span className="block text-primary bg-clip-text">
                Discutez avec vos
              </span>
              <span className="block mt-2">
                Documents
              </span>
            </h1>

            {/* Subheading */}
            <p className="text-gray-500   max-w-2xl mx-auto text-lg leading-7  mb-4">
              Explorez, analysez et comprenez vos fichiers grâce à notre assistant IA. 
              Posez des questions et obtenez des réponses instantanées avec références.
            </p>

            {/* File type badges */}
            <div className="flex flex-wrap justify-center gap-2 mb-10">
              {fileTypes.map((type, index) => (
                <span 
                  key={type.name}
                  className={`${type.color} text-white text-xs font-semibold px-3 py-1 rounded-full shadow-sm animate-fade-in`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  {type.name}
                </span>
              ))}
            </div>
          </div>

          {/* Upload Zone */}
          <div 
            className="max-w-3xl mx-auto animate-fade-in"
            style={{ animationDelay: '200ms' }}
          >
            <div className={`
              relative p-8 rounded-2xl transition-all bg-gray-50 duration-300 ease-out border-2 border-dashed
              ${isDragging 
                ? 'bg-primary/5 border-2 border-primary shadow-2xl shadow-primary/20 scale-[1.02]' 
                : 'bg-white/80 backdrop-blur-sm border border-slate-200  hover:shadow-md hover:border-primary/30'
              }
            `}>
              {/* Decorative corner accents */}
              <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-primary rounded-tl-lg" />
              <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-primary rounded-tr-lg" />
              <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-primary rounded-bl-lg" />
              <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-primary rounded-br-lg" />

              <label
                htmlFor="dropzone-file"
                className="flex flex-col items-center justify-center py-12 cursor-pointer"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                {isUploading ? (
                  <div className="flex flex-col items-center">
                    <Loading />
                    <p className="mt-4 text-slate-600 font-medium">Téléchargement en cours...</p>
                  </div>
                ) : (
                  <>
                    {/* Upload Icon */}
                    <div className={`
                      w-20 h-20 rounded-2xl flex items-center justify-center mb-6 transition-all duration-300
                      ${isDragging 
                        ? 'bg-primary text-white scale-110 rotate-3' 
                        : 'bg-gradient-to-br from-primary/10 to-primary/5 text-primary'
                      }
                    `}>
                      <GoUpload className="w-10 h-10" />
                    </div>

                    {/* Upload Text */}
                    <div className="text-center">
                      <p className="text-xl font-semibold text-slate-800 mb-2">
                        {isDragging ? 'Déposez votre fichier ici' : 'Glissez et déposez votre fichier'}
                      </p>
                      <p className="text-slate-500 mb-4">
                        ou <span className="text-primary font-medium hover:underline">parcourez vos fichiers</span>
                      </p>
                      <p className="text-sm text-slate-400">
                        PDF, TXT, CSV, MD • Max 200MB
                      </p>
                    </div>
                  </>
                )}
                <input 
                  onChange={handleFileChange} 
                  id="dropzone-file" 
                  type="file" 
                  className="hidden"
                  accept=".pdf,.txt,.csv,.md" 
                />
              </label>
            </div>

            {/* CTA below upload */}
            {!token && (
              <div className="text-center mt-6">
                <p className="text-slate-500">
                  Vous avez déjà un compte?{' '}
                  <Link to="/user/login" className="text-primary font-semibold hover:underline inline-flex items-center gap-1">
                    Connectez-vous
                    <GoArrowRight className="w-4 h-4" />
                  </Link>
                </p>
              </div>
            )}
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-24 max-w-5xl mx-auto">
            {features.map((feature, index) => (
              <div 
                key={feature.title}
                className="group p-6 rounded-xl bg-white/60 backdrop-blur-sm border border-slate-100 hover:border-primary/20 hover:shadow-md transition-all duration-300 animate-fade-in"
                style={{ animationDelay: `${300 + index * 100}ms` }}
              >
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 text-primary flex items-center justify-center mb-4 group-hover:scale-110 group-hover:bg-primary group-hover:text-white transition-all duration-300">
                  {feature.icon}
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">{feature.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>

          {/* How it works section */}
          <div className="mt-32 text-center">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">Comment ça marche?</h2>
            <p className="text-slate-500 mb-12 max-w-xl mx-auto">
              Trois étapes simples pour commencer à interagir avec vos documents
            </p>
            
            <div className="flex flex-col md:flex-row items-center justify-center gap-8 md:gap-4">
              {/* Step 1 */}
              <div className="flex flex-col items-center max-w-xs animate-fade-in" style={{ animationDelay: '400ms' }}>
                <div className="w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold mb-4 shadow-md shadow-primary/30">
                  1
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">Téléchargez</h3>
                <p className="text-sm text-slate-500">Déposez votre document dans la zone de téléchargement</p>
              </div>

              {/* Connector */}
              <div className="hidden md:block w-24 h-0.5 bg-gradient-to-r from-primary to-primary/30 rounded-full" />

              {/* Step 2 */}
              <div className="flex flex-col items-center max-w-xs animate-fade-in" style={{ animationDelay: '500ms' }}>
                <div className="w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold mb-4 shadow-md shadow-primary/30">
                  2
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">Analysez</h3>
                <p className="text-sm text-slate-500">Notre IA analyse et indexe le contenu automatiquement</p>
              </div>

              {/* Connector */}
              <div className="hidden md:block w-24 h-0.5 bg-gradient-to-r from-primary/30 to-primary rounded-full" />

              {/* Step 3 */}
              <div className="flex flex-col items-center max-w-xs animate-fade-in" style={{ animationDelay: '600ms' }}>
                <div className="w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold mb-4 shadow-md shadow-primary/30">
                  3
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">Discutez</h3>
                <p className="text-sm text-slate-500">Posez vos questions et obtenez des réponses précises</p>
              </div>
            </div>
          </div>

          {/* Bottom CTA */}
          <div className="mt-32 text-center animate-fade-in" style={{ animationDelay: '700ms' }}>
            <div className="inline-flex flex-col sm:flex-row items-center gap-14 p-8 rounded-2xl bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 border border-primary/10">
              <div className="text-left">
                <h3 className="text-xl font-bold text-slate-900 mb-1">Prêt à commencer?</h3>
                <p className="text-slate-500">Créez votre compte gratuitement et explorez vos documents</p>
              </div>
              <Link 
                to="/user/register"
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary/90 transition-all duration-300 shadow-sm shadow-primary/30 hover:shadow-md hover:shadow-primary/40 hover:-translate-y-0.5"
              >
                S'inscrire gratuitement
                <GoArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-100 py-8 mt-16">
        <div className="container max-w-6xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-slate-500">
            <p>© 2025 By Mohamed ED DERYOUCH. Tous droits réservés.</p>
            <div className="flex items-center gap-6">
              <button type="button" className="hover:text-primary transition-colors cursor-pointer">Confidentialité</button>
              <button type="button" className="hover:text-primary transition-colors cursor-pointer">Conditions</button>
              <button type="button" className="hover:text-primary transition-colors cursor-pointer">Contact</button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
