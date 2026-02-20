import { User, UpdateUserData } from '@/types/user';
import { mockUser } from '@/lib/mockData';

class UserService {
  async getCurrentUser(): Promise<User> {
    // Simulate API call
    return new Promise((resolve) => {
      setTimeout(() => {
        const storedUser = localStorage.getItem('currentUser');
        if (storedUser) {
          resolve(JSON.parse(storedUser));
        } else {
          resolve(mockUser);
        }
      }, 500);
    });
  }

  async updateUser(userId: string, data: UpdateUserData): Promise<User> {
    // Simulate API call
    return new Promise((resolve) => {
      setTimeout(() => {
        const storedUser = localStorage.getItem('currentUser');
        const currentUser = storedUser ? JSON.parse(storedUser) : mockUser;
        
        const updatedUser = {
          ...currentUser,
          ...data,
        };
        
        localStorage.setItem('currentUser', JSON.stringify(updatedUser));
        resolve(updatedUser);
      }, 500);
    });
  }

  async acceptTerms(userId: string): Promise<User> {
    return this.updateUser(userId, {
      termsAccepted: true,
      termsAcceptedDate: new Date().toISOString(),
    });
  }

  async deleteAccount(userId: string): Promise<void> {
    // Simulate API call
    return new Promise((resolve) => {
      setTimeout(() => {
        localStorage.removeItem('currentUser');
        localStorage.removeItem('authToken');
        resolve();
      }, 500);
    });
  }
}

export const userService = new UserService();