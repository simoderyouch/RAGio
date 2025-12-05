import { create } from 'zustand';

const useUIStore = create((set) => ({
  // Sidebar state
  sidebarCollapsed: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  // Modal states
  modals: {},
  openModal: (modalId) => set((state) => ({
    modals: { ...state.modals, [modalId]: true }
  })),
  closeModal: (modalId) => set((state) => ({
    modals: { ...state.modals, [modalId]: false }
  })),
  isModalOpen: (modalId) => {
    const state = useUIStore.getState();
    return state.modals[modalId] || false;
  },
}));

export default useUIStore;

