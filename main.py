#!/usr/bin/env python3
"""
Monthly calendar with reminders - single-file Tkinter app.

Save as calendar_reminders.py and run:
    python calendar_reminders.py

Reminders are stored in reminders.json in the same folder.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import calendar
from datetime import datetime, date, time, timedelta
import json
import os
import uuid

REMINDERS_FILE = "reminders.json"
CHECK_INTERVAL_MS = 60 * 1000  # 60 seconds


def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return {}
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # ensure keys are strings and lists
            return {k: v for k, v in data.items()}
    except Exception:
        return {}


def save_reminders(reminders):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


def date_key(y, m, d):
    return f"{y:04d}-{m:02d}-{d:02d}"


class ReminderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monthly Calendar - Reminders")
        self.geometry("820x600")
        self.resizable(False, False)

        self.reminders = load_reminders()

        today = date.today()
        self.curr_year = today.year
        self.curr_month = today.month

        self.create_widgets()
        self.draw_calendar()
        self.check_due_reminders_loop()

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(padx=10, pady=10, fill="x")

        btn_prev = ttk.Button(header, text="◀ Prev", command=self.prev_month)
        btn_prev.pack(side="left")

        btn_next = ttk.Button(header, text="Next ▶", command=self.next_month)
        btn_next.pack(side="right")

        btn_today = ttk.Button(header, text="Today", command=self.go_today)
        btn_today.pack(side="right", padx=(0, 8))

        self.lbl_month = ttk.Label(header, text="", font=("Segoe UI", 16, "bold"))
        self.lbl_month.pack(side="left", expand=True)

        # calendar area
        self.cal_frame = ttk.Frame(self)
        self.cal_frame.pack(padx=10, pady=(0, 10), fill="both")

        # weekdays header
        days_frame = ttk.Frame(self.cal_frame)
        days_frame.pack(fill="x")
        for wd in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            lbl = ttk.Label(days_frame, text=wd, anchor="center", width=11, font=("Segoe UI", 10, "bold"))
            lbl.pack(side="left")

        # grid for days
        self.days_grid = ttk.Frame(self.cal_frame)
        self.days_grid.pack()

        # footer / legend
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=10, pady=6)
        ttk.Label(footer, text="Click a date to view/add reminders. Reminders saved to reminders.json").pack(side="left")
        ttk.Button(footer, text="Open reminders file", command=self.open_reminders_file).pack(side="right")

    def open_reminders_file(self):
        # tries to open file in default editor - best effort
        try:
            if os.name == "nt":
                os.startfile(REMINDERS_FILE)
            elif os.name == "posix":
                # Linux / Mac (will open using xdg-open/open)
                opener = "xdg-open" if os.system("which xdg-open >/dev/null 2>&1") == 0 else "open"
                os.system(f'{opener} "{REMINDERS_FILE}"')
            else:
                messagebox.showinfo("Open", f"Please open {REMINDERS_FILE} manually.")
        except Exception:
            messagebox.showinfo("Open", f"Please open {REMINDERS_FILE} manually.")

    def draw_calendar(self):
        # clear previous
        for child in self.days_grid.winfo_children():
            child.destroy()

        cal = calendar.Calendar(firstweekday=0)  # Monday first (0)
        month_days = cal.monthdayscalendar(self.curr_year, self.curr_month)

        self.lbl_month.config(text=f"{calendar.month_name[self.curr_month]} {self.curr_year}")

        for row_idx, week in enumerate(month_days):
            row_frame = ttk.Frame(self.days_grid)
            row_frame.pack(fill="x")
            for col_idx, day in enumerate(week):
                frame = ttk.Frame(row_frame, borderwidth=1, relief="solid")
                frame.pack(side="left", padx=1, pady=1)

                btn_text = str(day) if day != 0 else ""
                # display day number and quick count of reminders
                if day == 0:
                    btn = ttk.Label(frame, text="", anchor="center", width=11, padding=10)
                    btn.pack()
                else:
                    dk = date_key(self.curr_year, self.curr_month, day)
                    rcount = len(self.reminders.get(dk, []))
                    txt = f"{day}\n{rcount} reminder{'s' if rcount != 1 else ''}" if rcount else f"{day}\n"
                    btn = ttk.Button(frame, text=txt, width=11, command=lambda d=day: self.open_day_window(d))
                    btn.pack(padx=2, pady=2, ipadx=3, ipady=8)

                    # highlight today
                    today = date.today()
                    if self.curr_year == today.year and self.curr_month == today.month and day == today.day:
                        btn.config(style="Today.TButton")

        # style for today
        s = ttk.Style(self)
        s.configure("Today.TButton", foreground="black", background="#ffefc3")
        s.map("Today.TButton",
              background=[('active', '#ffe88f')])

    def prev_month(self):
        if self.curr_month == 1:
            self.curr_month = 12
            self.curr_year -= 1
        else:
            self.curr_month -= 1
        self.draw_calendar()

    def next_month(self):
        if self.curr_month == 12:
            self.curr_month = 1
            self.curr_year += 1
        else:
            self.curr_month += 1
        self.draw_calendar()

    def go_today(self):
        t = date.today()
        self.curr_year = t.year
        self.curr_month = t.month
        self.draw_calendar()

    def open_day_window(self, day):
        dk = date_key(self.curr_year, self.curr_month, day)
        DayWindow(self, dk, self.reminders, on_save=self.on_reminders_changed)

    def on_reminders_changed(self):
        save_reminders(self.reminders)
        self.draw_calendar()

    def check_due_reminders_loop(self):
        """
        Periodically check reminders and show a popup for due items.
        """
        now = datetime.now()
        today_k = date_key(now.year, now.month, now.day)
        todays = self.reminders.get(today_k, [])
        triggered = []
        for r in todays:
            # each reminder stores: id, time (HH:MM), text, notified (bool)
            try:
                rtime = datetime.strptime(r["time"], "%H:%M").time()
            except Exception:
                continue
            # if reminder time <= now and not yet notified
            if (rtime.hour, rtime.minute) <= (now.hour, now.minute) and not r.get("notified", False):
                triggered.append(r)

        for r in triggered:
            # Show popup
            messagebox.showinfo("Reminder", f"{r['time']} — {r['text']}")
            r["notified"] = True

        # Also reset notifications for future dates not relevant (if user edited)
        # Save if any changes
        if triggered:
            save_reminders(self.reminders)
            self.draw_calendar()

        # schedule next check
        self.after(CHECK_INTERVAL_MS, self.check_due_reminders_loop)


class DayWindow(tk.Toplevel):
    def __init__(self, parent, datekey, reminders_dict, on_save=None):
        super().__init__(parent)
        self.title(f"Reminders for {datekey}")
        self.resizable(False, False)
        self.datekey = datekey
        self.reminders_dict = reminders_dict
        self.on_save = on_save

        self.create_widgets()
        self.load_list()

    def create_widgets(self):
        pad = {"padx": 10, "pady": 6}
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10)

        ttk.Label(frame, text=self.datekey, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, **pad)

        self.listbox = tk.Listbox(frame, width=50, height=10)
        self.listbox.grid(row=1, column=0, columnspan=3, **pad)

        ttk.Button(frame, text="Add", command=self.add_reminder).grid(row=2, column=0, **pad)
        ttk.Button(frame, text="Edit", command=self.edit_selected).grid(row=2, column=1, **pad)
        ttk.Button(frame, text="Delete", command=self.delete_selected).grid(row=2, column=2, **pad)

        ttk.Separator(frame, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(frame, text="Close", command=self.close).grid(row=4, column=2, sticky="e", pady=(8, 0))

    def load_list(self):
        self.listbox.delete(0, tk.END)
        items = self.reminders_dict.get(self.datekey, [])
        # sort by time
        items = sorted(items, key=lambda r: r.get("time", "00:00"))
        for r in items:
            display = f"[{r.get('time','')}] {r.get('text','')}"
            self.listbox.insert(tk.END, display)

    def add_reminder(self):
        # ask for time and text
        ts = simpledialog.askstring("Time (HH:MM AM/PM)", "Enter time (e.g., 08:30 AM)", parent=self)
        if not ts:
            return
        try:
            # convert AM/PM to 24-hour
            t24 = datetime.strptime(ts.strip(), "%I:%M %p").strftime("%H:%M")
        except Exception:
            messagebox.showerror("Invalid", "Time must be in HH:MM AM/PM format (e.g., 08:30 AM).")
            return
        text = simpledialog.askstring("Reminder text", "Enter reminder text", parent=self)
        if not text:
            return

        r = {
            "id": str(uuid.uuid4()),
            "time": t24,
            "text": text,
            "notified": False
        }
        self.reminders_dict.setdefault(self.datekey, []).append(r)
        if self.on_save:
            self.on_save()
        self.load_list()

    def edit_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Edit", "Select a reminder to edit.")
            return
        idx = sel[0]
        items = sorted(self.reminders_dict.get(self.datekey, []), key=lambda r: r.get("time", "00:00"))
        r = items[idx]

        # convert stored 24-hour to AM/PM for editing
        t12 = datetime.strptime(r["time"], "%H:%M").strftime("%I:%M %p")
        ts = simpledialog.askstring("Time (HH:MM AM/PM)", "Edit time", initialvalue=t12, parent=self)
        if not ts:
            return
        try:
            t24 = datetime.strptime(ts.strip(), "%I:%M %p").strftime("%H:%M")
        except Exception:
            messagebox.showerror("Invalid", "Time must be in HH:MM AM/PM format (e.g., 08:30 AM).")
            return
        text = simpledialog.askstring("Reminder text", "Edit reminder text", initialvalue=r["text"], parent=self)
        if not text:
            return

        # update
        orig_list = self.reminders_dict.get(self.datekey, [])
        for orig in orig_list:
            if orig["id"] == r["id"]:
                orig["time"] = t24
                orig["text"] = text
                orig["notified"] = False
                break

        if self.on_save:
            self.on_save()
        self.load_list()


    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Delete", "Select a reminder to delete.")
            return
        idx = sel[0]
        items = sorted(self.reminders_dict.get(self.datekey, []), key=lambda r: r.get("time", "00:00"))
        r = items[idx]

        if messagebox.askyesno("Confirm", f"Delete reminder: [{r['time']}] {r['text']}?"):
            # remove from original list by id
            orig_list = self.reminders_dict.get(self.datekey, [])
            orig_list = [x for x in orig_list if x["id"] != r["id"]]
            if orig_list:
                self.reminders_dict[self.datekey] = orig_list
            else:
                self.reminders_dict.pop(self.datekey, None)
            if self.on_save:
                self.on_save()
            self.load_list()

    def close(self):
        self.destroy()


if __name__ == "__main__":
    app = ReminderApp()
    app.mainloop()
