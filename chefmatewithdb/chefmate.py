import hashlib
import json
import re
import tkinter as tk
import sqlite3
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

COLORS = {
    "background": "#F4F1EA",
    "primary": "#2C3531",
    "accent": "#D05A3F",
    "accent_hover": "#B84A31",
    "card_bg": "#FFFFFF",
    "input_bg": "#FAF8F5",
    "text_dark": "#2C3531",
    "muted": "#7A847F",
    "line": "#E3DDD3",
}

TITLE_FONT = ("Segoe UI", 16, "bold")
HEADING_FONT = ("Segoe UI", 20, "bold")
BODY_FONT = ("Segoe UI", 10)
SUBTITLE_FONT = ("Segoe UI", 9)

class User:
    def __init__(
        self, username, password, role="user", full_name="", email="",
        password_hash=None,
    ):
        self.username = username
        self.email = email
        self.full_name = full_name or username
        self.password_hash = (
            password_hash or hashlib.sha256(password.encode()).hexdigest()
        )
        self.role = role


class Recipe:
    def __init__(
        self,
        recipe_id,
        name,
        ingredients,
        steps,
        cooking_time,
        category="Main dish",
        prep_time="",
        servings=4,
        description="",
        status="Published",
        author="ADMIN",
        posted_at=None,
        database_id=None,
    ):
        self.recipe_id = recipe_id
        self.name = name
        self.ingredients = ingredients
        self.steps = steps
        self.cooking_time = str(cooking_time).strip()
        self.category = category
        self.prep_time = str(prep_time).strip()
        self.servings = servings
        self.description = description
        self.status = status
        self.author = author
        self.posted_at = posted_at or datetime.now()
        self.database_id = database_id


class AuthManager:
    def __init__(self, connection):
        self.connection = connection
        self.users = {}
        default_accounts = [
            ("admin", "admin123", "admin", "admin@chefmate.com", "Admin"),
            ("demo", "demo123", "user", "demo@chefmate.com", "Demo Cook"),
            (
                "gordonramsay", "gordon123", "user",
                "gordonramsay@gmail.com", "Gordon Ramsay",
            ),
        ]
        for username, password, role, email, full_name in default_accounts:
            account_exists = self.connection.execute(
                "SELECT 1 FROM accounts WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if not account_exists:
                user = User(username, password, role, full_name, email)
                self.connection.execute(
                    """
                    INSERT INTO accounts
                        (username, full_name, email, password_hash, role)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user.username, user.full_name, user.email,
                        user.password_hash, user.role,
                    ),
                )
        self.connection.commit()

        rows = self.connection.execute(
            """
            SELECT username, full_name, email, password_hash, role
            FROM accounts
            """
        ).fetchall()
        for row in rows:
            user = User(
                row["username"], "", row["role"], row["full_name"], row["email"],
                password_hash=row["password_hash"],
            )
            self.users[user.username.casefold()] = user

    def login(self, username, password):
        key = username.strip().lower()
        user = self.users.get(key)
        if user is None:
            user = next(
                (item for item in self.users.values() if item.email.lower() == key),
                None,
            )
        if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
            return user
        return None

    def register(self, username, password, role="user", email="", full_name=""):
        clean_name = username.strip()
        clean_email = email.strip().lower()
        if len(clean_name) < 3 or len(clean_name) > 20:
            raise ValueError("Username must be between 3 and 20 characters.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        if clean_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", clean_email):
            raise ValueError("Enter a valid email address.")

        key = clean_name.lower()
        if key in self.users:
            raise ValueError("Username already exists.")
        if clean_email and any(user.email.lower() == clean_email for user in self.users.values()):
            raise ValueError("An account with this email already exists.")

        user = User(clean_name, password, role, full_name.strip(), clean_email)
        try:
            self.connection.execute(
                """
                INSERT INTO accounts
                    (username, full_name, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user.username, user.full_name, user.email,
                    user.password_hash, user.role,
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            raise ValueError("Username or email already exists in the database.") from error
        self.users[key] = user
        return user

    def delete_user(self, username, requesting_user):
        if requesting_user is None or requesting_user.role != "admin":
            raise PermissionError("Only an admin can delete user accounts.")

        key = username.casefold()
        user = self.users.get(key)
        if user is None:
            raise ValueError("This account no longer exists.")
        if user.role != "user":
            raise PermissionError("Admin accounts cannot be deleted here.")

        try:
            self.connection.execute(
                "DELETE FROM accounts WHERE username = ?",
                (user.username,),
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            raise
        del self.users[key]


class RecipeManager:
    def __init__(self, connection):
        self.connection = connection
        self.recipes = [
            Recipe(
                1,
                "Chicken Adobo",
                ["manok", "toyo", "suka", "bawang", "dahon ng laurel"],
                ["Pagsamahin ang manok, toyo, suka, bawang, at dahon ng laurel.",
                 "Pakuluan sa mahinang apoy hanggang lumambot ang manok at lumapot ang sarsa.",
                 "Ihain nang mainit kasama ng kanin."],
                "50 minuto",
                "Dinner",
                prep_time="10 minuto",
                servings=4,
                description="Paboritong pagkaing Pilipino na may malinamnam at bahagyang maasim na sarsa.",
            ),
            Recipe(
                2,
                "Garlic Butter Shrimp",
                ["hipon", "bawang", "mantikilya", "kalamansi"],
                ["Tunawin ang mantikilya at igisa ang bawang.",
                 "Idagdag ang hipon at lutuin hanggang maging kulay rosas.",
                 "Pigaan ng kalamansi at ihain."],
                "30 minuto",
                "Dinner",
                prep_time="10 minuto",
                servings=3,
                description="Malinamnam na hipon na hinaluan ng mabangong bawang at mantikilya.",
            ),
            Recipe(
                3,
                "Tomato Egg Pasta",
                ["pasta", "kamatis", "itlog", "bawang"],
                ["Pakuluan ang pasta hanggang lumambot.",
                 "Igisa ang kamatis at bawang sa kawali.",
                 "Ihalo ang pasta at lagyan ng pritong itlog sa ibabaw."],
                "25 minuto",
                "Lunch",
                prep_time="10 minuto",
                servings=2,
                description="Madaling lutuin na pasta na may kamatis at itlog.",
            ),
            Recipe(
                4,
                "Vegetable Fried Rice",
                ["kanin", "karot", "gisantes", "itlog", "toyo"],
                ["Iprito ang itlog habang hinahalo at itabi muna.",
                 "Igisa ang mga gulay, saka idagdag ang kanin at toyo.",
                 "Ibalik ang itlog sa kawali, haluin, at ihain."],
                "20 minuto",
                "Lunch",
                prep_time="10 minuto",
                servings=3,
                description="Mabilis lutuin at makulay na putahe ng kanin at gulay.",
            ),
            Recipe(
                5,
                "Banana Pancakes",
                ["saging", "harina", "itlog", "gatas"],
                ["Durugin ang saging at ihalo sa masa.",
                 "Ibuhos ang masa sa pinainit na kawali.",
                 "Baligtarin kapag may mga bula na at lutuin hanggang maging kulay ginto."],
                "20 minuto",
                "Breakfast",
                prep_time="10 minuto",
                servings=4,
                description="Malambot na pancake na pinatamis ng saging.",
            ),
        ]
        rows = self.connection.execute(
            """
            SELECT recipe_id, account_id, name, ingredients, instructions,
                   category, cooking_time, status, posted_at, prep_time,
                   servings, description
            FROM recipes
            ORDER BY recipe_id
            """
        ).fetchall()
        for row in rows:
            try:
                ingredients = json.loads(row["ingredients"])
                if not isinstance(ingredients, list):
                    raise ValueError("Ingredients are not a list.")
            except (json.JSONDecodeError, ValueError):
                ingredients = [
                    item.strip() for item in row["ingredients"].split(",")
                    if item.strip()
                ]
            try:
                steps = json.loads(row["instructions"])
                if not isinstance(steps, list):
                    raise ValueError("Instructions are not a list.")
            except (json.JSONDecodeError, ValueError):
                steps = [row["instructions"]] if row["instructions"] else []

            account = self.connection.execute(
                "SELECT username FROM accounts WHERE account_id = ?",
                (row["account_id"],),
            ).fetchone()
            if account is None:
                continue
            runtime_id = max(recipe.recipe_id for recipe in self.recipes) + 1
            self.recipes.append(
                Recipe(
                    runtime_id, row["name"], ingredients, steps,
                    row["cooking_time"], row["category"], status=row["status"],
                    prep_time=row["prep_time"], servings=row["servings"],
                    description=row["description"],
                    author=account["username"],
                    posted_at=datetime.fromisoformat(row["posted_at"]),
                    database_id=row["recipe_id"],
                )
            )
        self.next_id = max(recipe.recipe_id for recipe in self.recipes) + 1

    def get_all(self):
        return list(self.recipes)

    def get_categories(self):
        categories = ["Breakfast", "Lunch", "Dinner"]
        custom_categories = sorted(
            {
                recipe.category for recipe in self.recipes
                if recipe.category and recipe.category not in categories
            }
        )
        return categories + custom_categories

    def get_by_id(self, recipe_id):
        return next((r for r in self.recipes if r.recipe_id == recipe_id), None)

    def get_by_author(self, username):
        return [
            recipe for recipe in self.recipes
            if recipe.author.casefold() == username.casefold()
        ]

    @staticmethod
    def can_modify(recipe, user):
        return user is not None and (
            user.role == "admin" or recipe.author.casefold() == user.username.casefold()
        )

    def search(self, query="", mode="Any", category="All Categories", status=None):
        q = query.strip().lower()
        terms = [term.strip() for term in q.split(",") if term.strip()]
        results = []
        for recipe in self.recipes:
            if status and recipe.status.lower() != status.lower():
                continue
            if category != "All Categories" and recipe.category != category:
                continue

            if mode == "Dish name":
                matches = not q or q in recipe.name.lower()
            elif mode == "Ingredients":
                matches = all(
                    any(term in ingredient.lower() for ingredient in recipe.ingredients)
                    for term in terms
                ) if terms else True
            else:
                matches = (
                    not q
                    or q in recipe.name.lower()
                    or q in recipe.category.lower()
                    or any(q in ingredient.lower() for ingredient in recipe.ingredients)
                )
            if matches:
                results.append(recipe)
        return results

    def add_recipe(
        self, name, ingredients, steps, cooking_time, category,
        prep_time="", servings=4, description="", status="Published", author="ADMIN",
    ):
        self._validate(name, ingredients, steps, cooking_time, category, prep_time, servings)
        recipe = Recipe(
            self.next_id, name.strip(), ingredients, steps, cooking_time, category.strip(),
            prep_time, servings, description.strip(), status, author,
        )
        account = self.connection.execute(
            "SELECT account_id FROM accounts WHERE username = ? COLLATE NOCASE",
            (author,),
        ).fetchone()
        if account is None:
            raise ValueError("The recipe author account does not exist in the database.")
        try:
            cursor = self.connection.execute(
                """
                INSERT INTO recipes
                    (account_id, name, ingredients, instructions, category,
                     cooking_time, status, posted_at, prep_time, servings, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account["account_id"], recipe.name,
                    json.dumps(recipe.ingredients, ensure_ascii=False),
                    json.dumps(recipe.steps, ensure_ascii=False),
                    recipe.category, recipe.cooking_time, recipe.status,
                    recipe.posted_at.isoformat(sep=" ", timespec="seconds"),
                    recipe.prep_time, recipe.servings, recipe.description,
                ),
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            raise
        recipe.database_id = cursor.lastrowid
        self.recipes.append(recipe)
        self.next_id += 1
        return recipe

    def update_recipe(
        self, recipe_id, name, ingredients, steps, cooking_time, category,
        prep_time=None, servings=None, description=None, status=None, user=None,
    ):
        recipe = self.get_by_id(recipe_id)
        if recipe is None:
            raise ValueError("This recipe no longer exists.")
        if not self.can_modify(recipe, user):
            raise PermissionError("You can only edit recipes that you posted.")
        prep_time = recipe.prep_time if prep_time is None else prep_time
        servings = recipe.servings if servings is None else servings
        description = recipe.description if description is None else description
        status = recipe.status if status is None else status
        self._validate(name, ingredients, steps, cooking_time, category, prep_time, servings)
        updated_recipe = Recipe(
            recipe.recipe_id, name.strip(), ingredients, steps, cooking_time,
            category.strip(), prep_time, servings, description.strip(), status,
            recipe.author, recipe.posted_at, recipe.database_id,
        )
        if recipe.database_id is not None:
            try:
                self.connection.execute(
                    """
                    UPDATE recipes
                    SET name = ?, ingredients = ?, instructions = ?, category = ?,
                        cooking_time = ?, status = ?, prep_time = ?, servings = ?,
                        description = ?
                    WHERE recipe_id = ?
                    """,
                    (
                        updated_recipe.name,
                        json.dumps(updated_recipe.ingredients, ensure_ascii=False),
                        json.dumps(updated_recipe.steps, ensure_ascii=False),
                        updated_recipe.category, updated_recipe.cooking_time,
                        updated_recipe.status, updated_recipe.prep_time,
                        updated_recipe.servings, updated_recipe.description,
                        recipe.database_id,
                    ),
                )
                self.connection.commit()
            except sqlite3.Error:
                self.connection.rollback()
                raise
        recipe.name = updated_recipe.name
        recipe.ingredients = updated_recipe.ingredients
        recipe.steps = updated_recipe.steps
        recipe.cooking_time = updated_recipe.cooking_time
        recipe.category = updated_recipe.category
        recipe.prep_time = updated_recipe.prep_time
        recipe.servings = updated_recipe.servings
        recipe.description = updated_recipe.description
        recipe.status = updated_recipe.status
        return recipe

    @staticmethod
    def _validate(name, ingredients, steps, cooking_time, category, prep_time, servings):
        if not name.strip() or not ingredients or not steps or not category.strip():
            raise ValueError("Fill in the recipe name, category, ingredients, and instructions.")
        if cooking_time is None or not str(cooking_time).strip():
            raise ValueError("Enter a cook time, for example, 1 hour.")
        if servings <= 0:
            raise ValueError("Servings must be a positive number.")

    def delete_recipe(self, recipe_id, user):
        recipe = self.get_by_id(recipe_id)
        if recipe is None:
            raise ValueError("This recipe no longer exists.")
        if not self.can_modify(recipe, user):
            raise PermissionError("You can only delete recipes that you posted.")
        if recipe.database_id is not None:
            try:
                self.connection.execute(
                    "DELETE FROM recipes WHERE recipe_id = ?",
                    (recipe.database_id,),
                )
                self.connection.commit()
            except sqlite3.Error:
                self.connection.rollback()
                raise
        self.recipes.remove(recipe)

    def delete_by_author(self, username, user):
        if user is None or user.role != "admin":
            raise PermissionError("Only an admin can delete another user's recipes.")
        recipes = self.get_by_author(username)
        self.recipes = [
            recipe for recipe in self.recipes
            if recipe.author.casefold() != username.casefold()
        ]
        return len(recipes)


class RecipeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChefMate - Recipe Finder")
        self.geometry("1080x720")
        self.minsize(960, 680)
        self.configure(bg=COLORS["background"])

        database_path = Path(__file__).with_name("chefmate.db")
        self.connection = sqlite3.connect(str(database_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            );

            CREATE TABLE IF NOT EXISTS recipes (
                recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL,
                category TEXT NOT NULL,
                cooking_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Published',
                posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                prep_time TEXT NOT NULL DEFAULT '',
                servings INTEGER NOT NULL DEFAULT 4,
                description TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (account_id)
                    REFERENCES accounts (account_id)
                    ON DELETE CASCADE
            );
            """
        )
        recipe_columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(recipes)")
        }
        for column, definition in (
            ("prep_time", "TEXT NOT NULL DEFAULT ''"),
            ("servings", "INTEGER NOT NULL DEFAULT 4"),
            ("description", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in recipe_columns:
                self.connection.execute(
                    f"ALTER TABLE recipes ADD COLUMN {column} {definition}"
                )
        self.connection.commit()

        self.auth = AuthManager(self.connection)
        self.manager = RecipeManager(self.connection)
        self.current_user = None
        self._configure_styles()
        
        self.container = ttk.Frame(self, style="App.TFrame")
        self.container.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.close_database)
        self.show_login()

    def close_database(self):
        self.connection.close()
        self.destroy()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["background"])
        style.configure("Panel.TFrame", background=COLORS["card_bg"])
        style.configure(
            "TLabel", background=COLORS["background"], foreground=COLORS["text_dark"],
            font=BODY_FONT,
        )
        style.configure(
            "Panel.TLabel", background=COLORS["card_bg"], foreground=COLORS["text_dark"],
            font=BODY_FONT,
        )
        style.configure(
            "Title.TLabel", background=COLORS["background"], foreground=COLORS["primary"],
            font=TITLE_FONT,
        )
        style.configure(
            "Heading.TLabel", background=COLORS["background"], foreground=COLORS["primary"],
            font=HEADING_FONT,
        )
        style.configure(
            "PanelHeading.TLabel", background=COLORS["card_bg"], foreground=COLORS["primary"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "TButton", font=("Segoe UI", 9, "bold"), padding=(12, 8),
            background=COLORS["accent"], foreground=COLORS["card_bg"], borderwidth=0, relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent_hover"])],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.configure(
            "Secondary.TButton", background=COLORS["primary"], foreground=COLORS["card_bg"],
            font=("Segoe UI", 9, "bold"), padding=(12, 8),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#1A211E"), ("pressed", "#1A211E")]
        )
        style.configure(
            "Treeview", rowheight=36, font=BODY_FONT,
            background=COLORS["card_bg"], fieldbackground=COLORS["card_bg"], foreground=COLORS["text_dark"],
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading", font=("Segoe UI", 10, "bold"),
            background="#EAE5DC", foreground=COLORS["primary"], padding=8, relief="flat",
        )
        style.map("Treeview", background=[("selected", "#EFECE6")], foreground=[("selected", COLORS["primary"])])
        style.configure(
            "TEntry", fieldbackground=COLORS["input_bg"], foreground=COLORS["text_dark"],
            padding=8, relief="flat",
        )
        style.configure(
            "TCombobox", fieldbackground=COLORS["input_bg"], foreground=COLORS["text_dark"],
            padding=6, relief="flat",
        )

    def clear_frame(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_login(self):
        self.current_user = None
        self.clear_frame()
        LoginFrame(self.container, self).pack(fill="both", expand=True)

    def show_dashboard(self):
        self.clear_frame()
        DashboardFrame(self.container, self).pack(fill="both", expand=True)


class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="App.TFrame", padding=40)
        self.controller = controller
        self.register_mode = False

        outer_container = ttk.Frame(self, style="App.TFrame")
        outer_container.place(relx=0.5, rely=0.5, anchor="center")

        self.card = ttk.Frame(outer_container, style="Panel.TFrame", padding=(48, 36))
        self.card.pack(fill="both", expand=True)

        self.logo_label = ttk.Label(
            self.card, text="ChefMate", style="Panel.TLabel", font=("Segoe UI", 26, "bold"), foreground=COLORS["accent"],
        )
        self.logo_label.pack(anchor="center", pady=(0, 2))
        
        self.subtitle_brand = ttk.Label(
            self.card, text="Your Personal Recipe Companion", style="Panel.TLabel", font=SUBTITLE_FONT, foreground=COLORS["muted"],
        )
        self.subtitle_brand.pack(anchor="center", pady=(0, 24))

        self.title_label = ttk.Label(
            self.card, text="Welcome Back", style="Panel.TLabel",
            font=("Segoe UI", 16, "bold"), foreground=COLORS["primary"],
        )
        self.title_label.pack(anchor="w", pady=(0, 16))

        self.fields = ttk.Frame(self.card, style="Panel.TFrame")
        self.fields.pack(fill="x")
        
        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)
        
        self.name_row, _ = self._add_field("Full Name", self.name_var)
        self.email_row, self.email_entry = self._add_field("Email address or username", self.email_var)
        self.email_label = self.email_row.winfo_children()[0]
        self.password_row, self.password_entry = self._add_field(
            "Password", self.password_var, show="*",
        )
        self.confirm_row, self.confirm_entry = self._add_field(
            "Confirm password", self.confirm_var, show="*",
        )
        
        show_pass_check = tk.Checkbutton(
            self.fields,
            text="Show passwords",
            variable=self.show_password_var,
            command=self.toggle_password_visibility,
            bg=COLORS["card_bg"],
            fg=COLORS["text_dark"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["card_bg"],
            font=SUBTITLE_FONT,
            bd=0,
        )
        show_pass_check.pack(anchor="w", pady=(4, 12))

        self.action_button = ttk.Button(self.card, text="Sign In", command=self.submit)
        self.action_button.pack(fill="x", pady=(4, 10))

        btn_frame = ttk.Frame(self.card, style="Panel.TFrame")
        btn_frame.pack(fill="x", pady=(4, 0))

        self.switch_button = tk.Button(
            btn_frame,
            text="Don't have an account? Create account",
            command=self.toggle_mode,
            bg=COLORS["card_bg"],
            fg=COLORS["accent"],
            activebackground=COLORS["card_bg"],
            activeforeground=COLORS["accent_hover"],
            bd=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        self.switch_button.pack(anchor="center", pady=(4, 8))

        guest_btn = tk.Button(
            btn_frame,
            text="Browse recipes as guest",
            command=self.guest_login,
            bg=COLORS["card_bg"],
            fg=COLORS["muted"],
            activebackground=COLORS["card_bg"],
            activeforeground=COLORS["text_dark"],
            bd=0,
            font=SUBTITLE_FONT,
            cursor="hand2",
        )
        guest_btn.pack(anchor="center")

        self.name_row.pack_forget()
        self.confirm_row.pack_forget()

    def _add_field(self, label, variable, show=None):
        row = ttk.Frame(self.fields, style="Panel.TFrame")
        row.pack(fill="x", pady=6)
        lbl = ttk.Label(row, text=label, style="PanelHeading.TLabel", font=("Segoe UI", 9, "bold"))
        lbl.pack(anchor="w", pady=(0, 2))
        entry = ttk.Entry(row, textvariable=variable, show=show, width=44)
        entry.pack(fill="x")
        return row, entry

    def toggle_password_visibility(self):
        mask = "" if self.show_password_var.get() else "*"
        self.password_entry.configure(show=mask)
        self.confirm_entry.configure(show=mask)

    def toggle_mode(self):
        self.register_mode = not self.register_mode
        if self.register_mode:
            self.title_label.configure(text="Create Account")
            self.name_row.pack(fill="x", pady=6, before=self.email_row)
            self.email_label.configure(text="Email address")
            self.confirm_row.pack(fill="x", pady=6)
            self.action_button.configure(text="Create Account")
            self.switch_button.configure(text="Already have an account? Sign In")
        else:
            self.title_label.configure(text="Welcome Back")
            self.name_row.pack_forget()
            self.email_label.configure(text="Email address or username")
            self.confirm_row.pack_forget()
            self.action_button.configure(text="Sign In")
            self.switch_button.configure(text="Don't have an account? Create account")

    def submit(self):
        if not self.register_mode:
            user = self.controller.auth.login(
                self.email_var.get(), self.password_var.get(),
            )
            if user:
                self.controller.current_user = user
                self.controller.show_dashboard()
            else:
                messagebox.showerror("Sign in failed", "Check your email/username and password.")
            return

        email = self.email_var.get().strip()
        password = self.password_var.get()
        full_name = self.name_var.get().strip()
        if not full_name:
            messagebox.showerror("Create account", "Enter your full name.")
            return
        if password != self.confirm_var.get():
            messagebox.showerror("Create account", "The passwords do not match.")
            return
        username = email.split("@", 1)[0].strip()
        try:
            user = self.controller.auth.register(
                username, password, email=email, full_name=full_name,
            )
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Create account", str(error))
            return
        self.controller.current_user = user
        self.controller.show_dashboard()

    def guest_login(self):
        self.controller.current_user = None
        self.controller.show_dashboard()


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, background=None):
        super().__init__(parent, style="App.TFrame")
        self.canvas = tk.Canvas(
            self, background=background or COLORS["background"], highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="App.TFrame")
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        if background:
            self.inner.configure(style="Panel.TFrame")
        self.inner.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_inner)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)


class DashboardFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="App.TFrame")
        self.controller = controller
        self.current_view = "Dashboard"

        self.sidebar = tk.Frame(self, width=210, bg=COLORS["primary"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.content_area = ttk.Frame(self, style="App.TFrame", padding=24)
        self.content_area.pack(side="left", fill="both", expand=True)
        self.load_home_view()

    def _build_sidebar(self):
        brand_frame = tk.Frame(self.sidebar, bg=COLORS["primary"])
        brand_frame.pack(fill="x", padx=16, pady=24)
        tk.Label(
            brand_frame, text="ChefMate", bg=COLORS["primary"],
            fg=COLORS["card_bg"], font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", self.load_home_view),
            ("SEARCH RECIPE", self.load_search_view),
        ]
        if self.controller.current_user:
            nav_items.append(("MY RECIPES", self.load_my_recipes_view))
        if self.controller.current_user and self.controller.current_user.role == "admin":
            nav_items.append(("RECIPE MANAGEMENT", self.load_manage_view))
            nav_items.append(("ACCOUNT MANAGEMENT", self.load_accounts_view))
            
        nav_container = tk.Frame(self.sidebar, bg=COLORS["primary"])
        nav_container.pack(fill="x", padx=12)

        for label, command in nav_items:
            btn = tk.Button(
                nav_container, text=label, command=command, relief="flat",
                bg=COLORS["primary"], fg="#C5CFC9",
                activebackground=COLORS["accent"], activeforeground=COLORS["card_bg"],
                font=("Segoe UI", 9, "bold"), anchor="w", padx=12, pady=10, cursor="hand2",
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[label] = btn

        bottom_frame = tk.Frame(self.sidebar, bg=COLORS["primary"])
        bottom_frame.pack(side="bottom", fill="x", padx=16, pady=20)

        user = self.controller.current_user
        if user:
            tk.Label(
                bottom_frame, text=f"Signed in as\n{user.full_name}", bg=COLORS["primary"],
                fg="#C5CFC9", font=("Segoe UI", 8), justify="left", wraplength=170,
            ).pack(anchor="w", pady=(0, 10))

        tk.Button(
            bottom_frame, text="Log Out", command=self.controller.show_login,
            relief="flat", bg="#3B4641", fg=COLORS["card_bg"],
            activebackground=COLORS["accent"], activeforeground=COLORS["card_bg"],
            font=("Segoe UI", 9, "bold"), padx=10, pady=8, cursor="hand2",
        ).pack(fill="x")

    def _activate_nav(self, key):
        for label, button in self.nav_buttons.items():
            is_active = label == key
            button.configure(
                bg=COLORS["accent"] if is_active else COLORS["primary"],
                fg=COLORS["card_bg"] if is_active else "#C5CFC9"
            )

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def _heading(self, title, subtitle=None):
        ttk.Label(self.content_area, text=title, style="Heading.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(self.content_area, text=subtitle, foreground=COLORS["muted"], font=BODY_FONT).pack(anchor="w", pady=(2, 16))
        else:
            ttk.Label(self.content_area, text="", style="App.TFrame").pack(pady=(0, 8))

    def _published(self):
        return sorted(
            (
                recipe for recipe in self.controller.manager.get_all()
                if recipe.status == "Published"
            ),
            key=lambda recipe: recipe.posted_at,
            reverse=True,
        )

    def _author_display_name(self, recipe):
        user = self.controller.auth.users.get(recipe.author.casefold())
        return user.full_name if user else recipe.author

    def load_home_view(self):
        self.current_view = "Dashboard"
        self._activate_nav("Dashboard")
        self.clear_content()
        self._heading("Community Recipes", "Discover recent dishes shared by home cooks")
        recipes = self._published()
        if not recipes:
            ttk.Label(self.content_area, text="No published recipes yet.").pack(
                anchor="w", pady=16,
            )
            return

        cards = ScrollableFrame(self.content_area)
        cards.pack(fill="both", expand=True)
        for recipe in recipes:
            row = tk.Frame(
                cards.inner, bg=COLORS["card_bg"], padx=16, pady=14,
                highlightthickness=1, highlightbackground=COLORS["line"],
            )
            row.pack(fill="x", pady=(0, 8))
            details = tk.Frame(row, bg=COLORS["card_bg"])
            details.pack(side="left", fill="x", expand=True)
            tk.Label(
                details, text=recipe.name, bg=COLORS["card_bg"], fg=COLORS["primary"],
                font=("Segoe UI", 13, "bold"), anchor="w",
            ).pack(anchor="w")
            tk.Label(
                details,
                text=(
                    f"{recipe.category}  •  Posted by {self._author_display_name(recipe)}"
                    f"  •  {recipe.posted_at.strftime('%b %d, %Y %I:%M %p')}"
                ),
                bg=COLORS["card_bg"], fg=COLORS["muted"], font=SUBTITLE_FONT, anchor="w",
            ).pack(anchor="w", pady=(3, 0))
            ttk.Button(
                row, text="View Recipe",
                command=lambda item=recipe: RecipeDetailsWindow(self, item),
            ).pack(side="right", padx=(12, 0))

    @staticmethod
    def _food_mark(category):
        icons = {
            "Breakfast": "☀",
            "Lunch": "⌁",
            "Dinner": "♨",
        }
        return icons.get(category, "•")

    def load_search_view(self):
        self.current_view = "SEARCH RECIPE"
        self._activate_nav("SEARCH RECIPE")
        self.clear_content()
        self._heading("Search Recipes", "Find recipes by name, category, or ingredients")

        filters = ttk.Frame(self.content_area, style="App.TFrame")
        filters.pack(fill="x", pady=(0, 16))
        
        query_var = tk.StringVar()
        category_var = tk.StringVar(value="All Categories")
        
        search_entry = ttk.Entry(filters, textvariable=query_var, width=30)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        category_values = ["All Categories"] + self.controller.manager.get_categories()
        category_combo = ttk.Combobox(
            filters, textvariable=category_var, values=category_values, state="readonly",
            width=20,
        )
        category_combo.pack(side="left", padx=(0, 10))

        table_frame = ttk.Frame(self.content_area, style="App.TFrame")
        table_frame.pack(fill="both", expand=True)
        
        columns = ("name", "category", "posted")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        tree.heading("name", text="Recipe Name")
        tree.heading("category", text="Category")
        tree.heading("posted", text="Date Posted")
        tree.column("name", width=340, anchor="w")
        tree.column("category", width=180, anchor="center")
        tree.column("posted", width=180, anchor="center")
        
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def refresh(*_args):
            tree.delete(*tree.get_children())
            for recipe in self.controller.manager.search(
                query_var.get(), category=category_var.get(), status="Published",
            ):
                tree.insert(
                    "", "end", iid=str(recipe.recipe_id),
                    values=(
                        recipe.name,
                        recipe.category,
                        recipe.posted_at.strftime("%b %d, %Y %I:%M %p"),
                    ),
                )

        search_btn = ttk.Button(filters, text="Search", command=refresh)
        search_btn.pack(side="left")
        
        query_var.trace_add("write", refresh)
        category_var.trace_add("write", refresh)

        def open_selected(_event=None):
            selected = tree.selection()
            if not selected:
                return
            recipe = self.controller.manager.get_by_id(int(selected[0]))
            if recipe:
                RecipeDetailsWindow(self, recipe)

        tree.bind("<Double-1>", open_selected)
        refresh()

    def load_manage_view(self):
        user = self.controller.current_user
        if user is None or user.role != "admin":
            messagebox.showwarning("Access restricted", "Recipe management is for admins only.")
            self.load_search_view()
            return
        self._load_recipe_management_view(
            "RECIPE MANAGEMENT",
            "Add, view, edit, and remove recipes from the platform",
            on_save=self.load_manage_view,
        )

    def load_accounts_view(self):
        user = self.controller.current_user
        if user is None or user.role != "admin":
            messagebox.showwarning("Access restricted", "Account management is for admins only.")
            self.load_search_view()
            return

        self.current_view = "ACCOUNT MANAGEMENT"
        self._activate_nav("ACCOUNT MANAGEMENT")
        self.clear_content()
        self._heading(
            "Account Management",
            "View user accounts and remove an account with its posted recipes.",
        )

        table_frame = ttk.Frame(self.content_area, style="App.TFrame")
        table_frame.pack(fill="both", expand=True)
        columns = ("username", "full_name", "email", "recipes")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        tree.heading("username", text="Username")
        tree.heading("full_name", text="Name")
        tree.heading("email", text="Email")
        tree.heading("recipes", text="Recipes")
        tree.column("username", width=150, anchor="w")
        tree.column("full_name", width=220, anchor="w")
        tree.column("email", width=260, anchor="w")
        tree.column("recipes", width=90, anchor="center")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def refresh():
            tree.delete(*tree.get_children())
            accounts = sorted(
                (
                    account for account in self.controller.auth.users.values()
                    if account.role == "user"
                ),
                key=lambda account: account.username.casefold(),
            )
            for account in accounts:
                recipe_count = len(
                    self.controller.manager.get_by_author(account.username)
                )
                tree.insert(
                    "", "end", iid=account.username.casefold(),
                    values=(
                        account.username,
                        account.full_name,
                        account.email,
                        recipe_count,
                    ),
                )
            if not accounts:
                tree.insert("", "end", values=("No user accounts", "", "", ""))

        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Delete account", "Select a user account first.")
                return
            account = self.controller.auth.users.get(selected[0])
            if account is None or account.role != "user":
                messagebox.showerror("Delete account", "Select a valid user account.")
                refresh()
                return
            recipe_count = len(
                self.controller.manager.get_by_author(account.username)
            )
            prompt = (
                f"Delete the account for {account.full_name} ({account.username})?"
            )
            if recipe_count:
                prompt += f"\n\nThis will also delete {recipe_count} posted recipe(s)."
            if not messagebox.askyesno("Delete account", prompt):
                return

            try:
                self.controller.auth.delete_user(account.username, user)
                self.controller.manager.delete_by_author(account.username, user)
            except (ValueError, PermissionError, sqlite3.Error) as error:
                messagebox.showerror("Delete account", str(error))
                refresh()
                return
            refresh()

        ttk.Button(
            self.content_area, text="Delete selected user",
            command=delete_selected, style="Secondary.TButton",
        ).pack(anchor="e", pady=(12, 0))
        refresh()

    def load_my_recipes_view(self):
        user = self.controller.current_user
        if user is None:
            messagebox.showwarning("Sign in required", "Sign in to post and manage your recipes.")
            self.load_search_view()
            return
        self._load_recipe_management_view(
            "MY RECIPES",
            "Manage your personal recipe submissions",
            author=user.username,
            on_save=self.load_my_recipes_view,
        )

    def _load_recipe_management_view(self, title, subtitle, author=None, on_save=None):
        self.current_view = title
        self._activate_nav(title)
        self.clear_content()
        self._heading(title, subtitle)

        body = ttk.Frame(self.content_area, style="App.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=320)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        editor_panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        editor_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        editor = RecipeEditor(
            editor_panel, self.controller.manager, self.controller.current_user,
            on_save=on_save,
        )
        editor.pack(fill="both", expand=True)

        list_panel = ttk.Frame(body, style="App.TFrame")
        list_panel.grid(row=0, column=1, sticky="nsew")
        list_panel.rowconfigure(2, weight=1)
        list_panel.columnconfigure(0, weight=1)
        
        ttk.Label(list_panel, text="Recipe Directory", style="PanelHeading.TLabel", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8),
        )
        
        filter_bar = ttk.Frame(list_panel, style="App.TFrame")
        filter_bar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        
        search_var = tk.StringVar()
        category_var = tk.StringVar(value="All Categories")
        status_var = tk.StringVar(value="All Status")
        
        ttk.Entry(filter_bar, textvariable=search_var, width=18).pack(side="left", padx=(0, 8))
        ttk.Combobox(
            filter_bar, textvariable=category_var,
            values=["All Categories"] + self.controller.manager.get_categories(),
            state="readonly", width=16,
        ).pack(side="left", padx=(0, 8))
        ttk.Combobox(
            filter_bar, textvariable=status_var,
            values=["All Status", "Published", "Draft"], state="readonly", width=12,
        ).pack(side="left")

        cards = ScrollableFrame(list_panel)
        cards.grid(row=2, column=0, sticky="nsew")

        def refresh(*_args):
            for child in cards.inner.winfo_children():
                child.destroy()
            selected_status = status_var.get()
            results = self.controller.manager.search(
                search_var.get(),
                category=category_var.get(),
                status=None if selected_status == "All Status" else selected_status,
            )
            if author:
                results = [
                    recipe for recipe in results
                    if recipe.author.casefold() == author.casefold()
                ]
            if not results:
                ttk.Label(cards.inner, text="No recipes match these filters.").pack(
                    anchor="w", pady=16,
                )
            for recipe in results:
                self._build_recipe_row(cards.inner, recipe, refresh)

        search_var.trace_add("write", refresh)
        category_var.trace_add("write", refresh)
        status_var.trace_add("write", refresh)
        refresh()

    def _build_recipe_row(self, parent, recipe, refresh):
        row = tk.Frame(
            parent, bg=COLORS["card_bg"], highlightthickness=1,
            highlightbackground=COLORS["line"], padx=12, pady=10,
        )
        row.pack(fill="x", pady=(0, 6))
        
        name_area = tk.Frame(row, bg=COLORS["card_bg"])
        name_area.pack(side="left", fill="x", expand=True)
        
        tk.Label(
            name_area, text=recipe.name, bg=COLORS["card_bg"],
            fg=COLORS["primary"], font=("Segoe UI", 11, "bold"), anchor="w",
        ).pack(anchor="w")
        
        tk.Label(
            name_area, text=f"{recipe.cooking_time}  •  {recipe.category}  •  {recipe.status}",
            bg=COLORS["card_bg"], fg=COLORS["muted"], font=SUBTITLE_FONT, anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(row, style="Panel.TFrame")
        actions.pack(side="right")
        
        ttk.Button(
            actions, text="View", width=6,
            command=lambda: RecipeDetailsWindow(self, recipe),
        ).pack(side="left", padx=3)
        ttk.Button(
            actions, text="Edit", width=6, style="Secondary.TButton",
            command=lambda: self._edit_recipe(recipe, refresh),
        ).pack(side="left", padx=3)
        ttk.Button(
            actions, text="Delete", width=6,
            command=lambda: self._delete_recipe(recipe, refresh),
        ).pack(side="left", padx=3)

    def _edit_recipe(self, recipe, refresh):
        if not self.controller.manager.can_modify(recipe, self.controller.current_user):
            messagebox.showerror("Edit recipe", "You can only edit recipes that you posted.")
            return
        RecipeFormWindow(
            self, self.controller.manager, recipe=recipe, on_save=refresh,
        )

    def _delete_recipe(self, recipe, refresh):
        if not self.controller.manager.can_modify(recipe, self.controller.current_user):
            messagebox.showerror("Delete recipe", "You can only delete recipes that you posted.")
            return
        if messagebox.askyesno("Delete recipe", f"Delete “{recipe.name}”?"):
            try:
                self.controller.manager.delete_recipe(
                    recipe.recipe_id, self.controller.current_user,
                )
            except (ValueError, PermissionError, sqlite3.Error) as error:
                messagebox.showerror("Delete recipe", str(error))
                return
            refresh()


class RecipeEditor(ttk.Frame):
    def __init__(self, parent, manager, user, on_save):
        super().__init__(parent, style="Panel.TFrame")
        self.manager = manager
        self.user = user
        self.on_save = on_save
        self.recipe = None
        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(self, text="Recipe Details", style="PanelHeading.TLabel", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 10),
        )
        fields = ScrollableFrame(self, background=COLORS["card_bg"])
        fields.pack(fill="both", expand=True)
        self.fields = fields.inner

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar(value="Breakfast")
        self.prep_var = tk.StringVar()
        self.cook_var = tk.StringVar()
        self.servings_var = tk.StringVar(value="4")
        self.status_var = tk.StringVar(value="Published")
        
        self._entry("Recipe Name *", self.name_var)
        
        ttk.Label(self.fields, text="Category *", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2),
        )
        self.category_combo = ttk.Combobox(
            self.fields, textvariable=self.category_var,
            values=self.manager.get_categories(), state="readonly",
        )
        self.category_combo.pack(fill="x")
        
        self._entry("Prep Time", self.prep_var, placeholder="e.g. 15 mins")
        self._entry("Cook Time *", self.cook_var, placeholder="e.g. 30 mins")
        self._entry("Servings", self.servings_var)
        
        ttk.Label(self.fields, text="Short Description", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2),
        )
        self.description_text = tk.Text(
            self.fields, height=3, wrap="word", font=BODY_FONT,
            bg=COLORS["input_bg"], fg=COLORS["text_dark"], relief="flat", bd=0,
        )
        self.description_text.pack(fill="x")
        
        ttk.Label(self.fields, text="Ingredients * (one per line)", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2),
        )
        self.ingredients_text = tk.Text(
            self.fields, height=4, wrap="word", font=BODY_FONT,
            bg=COLORS["input_bg"], fg=COLORS["text_dark"], relief="flat", bd=0,
        )
        self.ingredients_text.pack(fill="x")
        
        ttk.Label(self.fields, text="Instructions * (one per line)", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2),
        )
        self.steps_text = tk.Text(
            self.fields, height=5, wrap="word", font=BODY_FONT,
            bg=COLORS["input_bg"], fg=COLORS["text_dark"], relief="flat", bd=0,
        )
        self.steps_text.pack(fill="x")
        
        ttk.Label(self.fields, text="Status", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2),
        )
        ttk.Combobox(
            self.fields, textvariable=self.status_var,
            values=["Published", "Draft"], state="readonly",
        ).pack(fill="x")

        buttons = ttk.Frame(self, style="Panel.TFrame")
        buttons.pack(fill="x", pady=(14, 0))
        
        ttk.Button(buttons, text="Save Recipe", command=self.save).pack(
            side="left", fill="x", expand=True, padx=(0, 6),
        )
        ttk.Button(buttons, text="Clear", style="Secondary.TButton", command=self.clear).pack(
            side="left",
        )

    def _entry(self, label, variable, placeholder=""):
        ttk.Label(self.fields, text=label, style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 2)
        )
        entry = ttk.Entry(self.fields, textvariable=variable)
        entry.pack(fill="x")
        if placeholder:
            entry.insert(0, placeholder)
            entry.configure(foreground=COLORS["muted"])
            entry.bind("<FocusIn>", lambda _event, e=entry, p=placeholder: self._clear_placeholder(e, p))

    @staticmethod
    def _clear_placeholder(entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.configure(foreground=COLORS["text_dark"])

    def set_recipe(self, recipe):
        self.recipe = recipe
        self.name_var.set(recipe.name)
        self.category_var.set(recipe.category)
        self.prep_var.set(str(recipe.prep_time))
        self.cook_var.set(str(recipe.cooking_time))
        self.servings_var.set(str(recipe.servings))
        self.status_var.set(recipe.status)
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", recipe.description)
        self.ingredients_text.delete("1.0", "end")
        self.ingredients_text.insert("1.0", "\n".join(recipe.ingredients))
        self.steps_text.delete("1.0", "end")
        self.steps_text.insert("1.0", "\n".join(recipe.steps))
        self.winfo_toplevel().title(f"Edit Recipe — {recipe.name}")

    def clear(self):
        self.recipe = None
        self.name_var.set("")
        self.category_var.set("Breakfast")
        self.prep_var.set("")
        self.cook_var.set("")
        self.servings_var.set("4")
        self.status_var.set("Published")
        for widget in (self.description_text, self.ingredients_text, self.steps_text):
            widget.delete("1.0", "end")

    def save(self):
        if self.user is None:
            messagebox.showerror("Recipe details", "Sign in to post a recipe.")
            return
        name = self.name_var.get().strip()
        category = self.category_var.get().strip()
        ingredients = [
            line.strip() for line in self.ingredients_text.get("1.0", "end").splitlines()
            if line.strip()
        ]
        steps = [
            line.strip() for line in self.steps_text.get("1.0", "end").splitlines()
            if line.strip()
        ]
        try:
            cooking_time = self.cook_var.get().strip()
            prep_time = self.prep_var.get().strip()
            servings = int(self.servings_var.get().strip() or "4")
            description = self.description_text.get("1.0", "end").strip()
            if self.recipe:
                self.manager.update_recipe(
                    self.recipe.recipe_id, name, ingredients, steps, cooking_time, category,
                    prep_time, servings, description, self.status_var.get(), self.user,
                )
            else:
                self.manager.add_recipe(
                    name, ingredients, steps, cooking_time, category,
                    prep_time, servings, description, self.status_var.get(),
                    self.user.username.upper(),
                )
        except (ValueError, PermissionError, sqlite3.Error) as error:
            messagebox.showerror("Recipe details", str(error) or "Enter valid recipe times.")
            return
        self.clear()
        self.on_save()


class RecipeDetailsWindow(tk.Toplevel):
    def __init__(self, parent, recipe):
        super().__init__(parent)
        self.title(recipe.name)
        self.geometry("520x600")
        self.minsize(400, 450)
        self.configure(bg=COLORS["background"])
        
        panel = ttk.Frame(self, style="Panel.TFrame", padding=24)
        panel.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            panel, text=recipe.name, style="Panel.TLabel",
            font=("Segoe UI", 18, "bold"), foreground=COLORS["primary"],
        ).pack(anchor="w")
        
        ttk.Label(
            panel,
            text=f"{recipe.category}  •  Prep: {recipe.prep_time or 'N/A'}  •  "
                 f"Cook: {recipe.cooking_time}  •  Serves {recipe.servings}",
            style="Panel.TLabel", foreground=COLORS["muted"], font=SUBTITLE_FONT,
        ).pack(anchor="w", pady=(4, 12))
        
        if recipe.description:
            ttk.Label(
                panel, text=recipe.description, style="Panel.TLabel", wraplength=460,
            ).pack(anchor="w", pady=(0, 12))
            
        ttk.Label(panel, text="Ingredients", style="PanelHeading.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(
            panel, text="\n".join(f"• {item}" for item in recipe.ingredients),
            style="Panel.TLabel", justify="left",
        ).pack(anchor="w", pady=(2, 14))
        
        ttk.Label(panel, text="Instructions", style="PanelHeading.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        steps = tk.Text(
            panel, height=8, wrap="word", font=BODY_FONT,
            bg=COLORS["input_bg"], fg=COLORS["text_dark"], relief="flat", bd=0,
        )
        steps.pack(fill="both", expand=True, pady=(4, 14))
        for index, step in enumerate(recipe.steps, 1):
            steps.insert("end", f"{index}. {step}\n\n")
        steps.configure(state="disabled")
        
        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")


class RecipeFormWindow(tk.Toplevel):
    def __init__(self, parent, manager, recipe=None, on_save=None):
        super().__init__(parent)
        self.title("Edit Recipe" if recipe else "Add Recipe")
        self.geometry("460x640")
        self.minsize(380, 480)
        self.configure(bg=COLORS["background"])
        
        editor = RecipeEditor(
            self, manager,
            getattr(parent.controller, "current_user", None),
            on_save=on_save or self.destroy,
        )
        editor.pack(fill="both", expand=True, padx=14, pady=14)
        if recipe:
            editor.set_recipe(recipe)


if __name__ == "__main__":
    app = RecipeApp()
    app.mainloop()