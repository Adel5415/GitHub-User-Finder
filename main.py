import json
import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

import requests

API_USER_URL = "https://api.github.com/users/{}"
API_SEARCH_URL = "https://api.github.com/search/users"
FAVORITES_FILE = "favorites.json"


class GitHubUserFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("900x600")

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Введите логин GitHub и нажмите «Поиск»")

        self.search_results = []
        self.favorites = self.load_favorites()

        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitHubUserFinderApp"
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

        self.create_widgets()
        self.update_favorites_list()

    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="Логин GitHub:").pack(side="left")

        self.search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=8, fill="x", expand=True)
        self.search_entry.bind("<Return>", self.start_search)

        self.search_button = ttk.Button(top_frame, text="Поиск", command=self.start_search)
        self.search_button.pack(side="left", padx=5)

        ttk.Button(top_frame, text="Очистить", command=self.clear_search).pack(side="left")

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Результаты
        results_frame = ttk.LabelFrame(main_frame, text="Результаты поиска")
        results_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.results_listbox = tk.Listbox(results_frame)
        self.results_listbox.pack(side="left", fill="both", expand=True)

        results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_listbox.yview)
        results_scroll.pack(side="right", fill="y")
        self.results_listbox.config(yscrollcommand=results_scroll.set)

        self.results_listbox.bind("<Double-Button-1>", lambda event: self.open_selected_user())

        results_buttons = ttk.Frame(results_frame)
        results_buttons.pack(fill="x", pady=8)

        ttk.Button(results_buttons, text="Открыть профиль", command=self.open_selected_user).pack(
            side="left", padx=3
        )
        ttk.Button(results_buttons, text="В избранное", command=self.add_to_favorites).pack(
            side="left", padx=3
        )

        # Избранное
        favorites_frame = ttk.LabelFrame(main_frame, text="Избранное")
        favorites_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.favorites_listbox = tk.Listbox(favorites_frame)
        self.favorites_listbox.pack(side="left", fill="both", expand=True)

        fav_scroll = ttk.Scrollbar(favorites_frame, orient="vertical", command=self.favorites_listbox.yview)
        fav_scroll.pack(side="right", fill="y")
        self.favorites_listbox.config(yscrollcommand=fav_scroll.set)

        self.favorites_listbox.bind("<Double-Button-1>", lambda event: self.open_selected_favorite())

        fav_buttons = ttk.Frame(favorites_frame)
        fav_buttons.pack(fill="x", pady=8)

        ttk.Button(fav_buttons, text="Открыть профиль", command=self.open_selected_favorite).pack(
            side="left", padx=3
        )
        ttk.Button(fav_buttons, text="Удалить", command=self.remove_from_favorites).pack(
            side="left", padx=3
        )
        ttk.Button(fav_buttons, text="Очистить всё", command=self.clear_favorites).pack(
            side="left", padx=3
        )

        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=6
        )
        status.pack(fill="x", side="bottom")

    def set_status(self, text):
        self.status_var.set(text)

    def clear_search(self):
        self.search_var.set("")
        self.search_results = []
        self.results_listbox.delete(0, tk.END)
        self.set_status("Поле поиска очищено.")

    def start_search(self, event=None):
        query = self.search_var.get().strip()

        if not query:
            messagebox.showwarning("Ошибка", "Поле поиска не должно быть пустым.")
            return

        self.search_button.config(state="disabled")
        self.set_status(f"Поиск: {query}")
        self.root.update_idletasks()

        try:
            users = self.find_users(query)
            self.show_results(users, query)
        except requests.exceptions.RequestException as e:
            self.search_button.config(state="normal")
            self.set_status("Ошибка поиска.")
            messagebox.showerror("Ошибка", f"Не удалось выполнить поиск:\n{e}")
        except Exception as e:
            self.search_button.config(state="normal")
            self.set_status("Ошибка поиска.")
            messagebox.showerror("Ошибка", f"Неожиданная ошибка:\n{e}")

        self.search_button.config(state="normal")

    def find_users(self, query):
        # 1. Сначала ищем точный логин
        exact_url = API_USER_URL.format(query)
        exact_response = requests.get(exact_url, headers=self.headers, timeout=15)

        if exact_response.status_code == 200:
            return [exact_response.json()]

        # Если не нашли пользователя — это не ошибка, идём дальше
        if exact_response.status_code != 404:
            exact_response.raise_for_status()

        # 2. Обычный поиск
        params = {
            "q": f"{query} in:login",
            "per_page": 20
        }
        search_response = requests.get(API_SEARCH_URL, headers=self.headers, params=params, timeout=15)
        search_response.raise_for_status()

        data = search_response.json()
        return data.get("items", [])

    def show_results(self, users, query):
        self.search_results = users
        self.results_listbox.delete(0, tk.END)

        if not users:
            self.results_listbox.insert(tk.END, "Ничего не найдено")
            self.set_status(f"По запросу «{query}» ничего не найдено.")
            return

        for user in users:
            self.results_listbox.insert(tk.END, user.get("login", "unknown"))

        self.results_listbox.selection_set(0)
        self.set_status(f"Найдено пользователей: {len(users)}")

    def get_selected_search_user(self):
        selected = self.results_listbox.curselection()
        if not selected:
            return None

        index = selected[0]
        if index >= len(self.search_results):
            return None

        return self.search_results[index]

    def get_selected_favorite(self):
        selected = self.favorites_listbox.curselection()
        if not selected:
            return None

        index = selected[0]
        if index >= len(self.favorites):
            return None

        return self.favorites[index]

    def add_to_favorites(self):
        user = self.get_selected_search_user()

        if not user:
            messagebox.showinfo("Выбор", "Сначала выберите пользователя из результатов поиска.")
            return

        login = user.get("login", "")

        for fav in self.favorites:
            if fav.get("login", "").lower() == login.lower():
                messagebox.showinfo("Избранное", "Этот пользователь уже есть в избранном.")
                return

        favorite_user = {
            "login": user.get("login", ""),
            "html_url": user.get("html_url", ""),
            "avatar_url": user.get("avatar_url", "")
        }

        self.favorites.append(favorite_user)
        self.save_favorites()
        self.update_favorites_list()
        self.set_status(f"Пользователь {login} добавлен в избранное.")

    def remove_from_favorites(self):
        user = self.get_selected_favorite()

        if not user:
            messagebox.showinfo("Выбор", "Сначала выберите пользователя из избранного.")
            return

        login = user.get("login", "")
        self.favorites.remove(user)
        self.save_favorites()
        self.update_favorites_list()
        self.set_status(f"Пользователь {login} удалён из избранного.")

    def clear_favorites(self):
        if not self.favorites:
            messagebox.showinfo("Избранное", "Избранное уже пустое.")
            return

        answer = messagebox.askyesno("Подтверждение", "Удалить всех пользователей из избранного?")
        if answer:
            self.favorites = []
            self.save_favorites()
            self.update_favorites_list()
            self.set_status("Избранное очищено.")

    def open_selected_user(self):
        user = self.get_selected_search_user()
        if not user:
            messagebox.showinfo("Выбор", "Сначала выберите пользователя из результатов поиска.")
            return

        url = user.get("html_url")
        if url:
            webbrowser.open(url)

    def open_selected_favorite(self):
        user = self.get_selected_favorite()
        if not user:
            messagebox.showinfo("Выбор", "Сначала выберите пользователя из избранного.")
            return

        url = user.get("html_url")
        if url:
            webbrowser.open(url)

    def update_favorites_list(self):
        self.favorites_listbox.delete(0, tk.END)

        if not self.favorites:
            self.favorites_listbox.insert(tk.END, "Избранное пусто")
            return

        for user in self.favorites:
            self.favorites_listbox.insert(tk.END, user.get("login", "unknown"))

    def load_favorites(self):
        if not os.path.exists(FAVORITES_FILE):
            return []

        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
        except Exception:
            pass

        return []

    def save_favorites(self):
        with open(FAVORITES_FILE, "w", encoding="utf-8") as file:
            json.dump(self.favorites, file, ensure_ascii=False, indent=2)


def main():
    root = tk.Tk()

    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = GitHubUserFinderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()