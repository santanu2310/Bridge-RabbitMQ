import { ref } from "vue";
import { defineStore } from "pinia";
import { useRouter } from "vue-router";
import axios from "axios";

export const useAuthStore = defineStore("authentication", () => {
	const isAuthenticated = ref(true);
	const isLoading = ref(true);
	const router = useRouter();
	const baseUrl = "http://localhost:8000/";

	const authAxios = axios.create({
		baseURL: "http://localhost:8000/",
		withCredentials: true,
	});

	const publicAxios = axios.create({
		baseURL: "http://localhost:8000/",
	});

	// Axios interceptor to catch unauthentication error and retry after retriving the auth tokens
	authAxios.interceptors.response.use(
		(response) => response, // Directly return successful responses.
		async (error) => {
			const originalRequest = error.config;

			if (
				(error.response.status === 401 ||
					error.response.status === 422) &&
				!originalRequest._retry
			) {
				originalRequest._retry = true; // Mark the request as retried to avoid infinite loops.

				try {
					// Request to server for new token pair
					await axios({
						method: "post",
						url: baseUrl + "users/refresh-token",
						withCredentials: true,
					});

					// Retry the original request with the new access token.
					return authAxios(originalRequest);
				} catch (refreshError) {
					console.error("Token refresh failed:", refreshError);
					router.push({ name: "login" });
					return Promise.reject(refreshError);
				}
			}
			return Promise.reject(error); // For all other errors, return the error as is.
		}
	);

	return {
		isAuthenticated,
		isLoading,
		authAxios,
		publicAxios,
	};
});
