import { create } from 'zustand';

const useFileStore = create((set, get) => ({
  handleUpload: async (selectedFile, axiosInstance) => {
    if (!selectedFile) {
      return { error: "No file selected." };
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    
    try {
      const response = await axiosInstance.post('/api/document/upload', formData);
      return response;
    } catch (error) {
      return error;
    }
  },
}));

export default useFileStore;

