#!/usr/bin/env python3
# Stickity Stacks – Frameless GTK4 sticky notes with stacking, persistence, styling, and deletion

import gi, json, os
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Pango

class StickyNote(Gtk.Window):
    def __init__(self):
        super().__init__(title="Stickity Stacks", decorated=False)
        self.set_default_size(260, 200)
        self.set_resizable(True)

        # Add CSS class to main window for more specific targeting
        self.add_css_class("sticky-note-window")

        # Persistence file
        self.data_file = "stickity_stacks_notes.json"
        # Default style values with better font fallbacks
        self.current_font = "Sans 15"
        self.current_fg   = "#1a1a1a"
        self.current_bg   = "#fffad1"
        # Load saved preferences before UI creation
        self.load_prefs()

        # Note stack management
        self.note_stack = []
        self.current_note_index = 0
        self.note_counter = 1

        # CSS provider at APPLICATION priority to override theme
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Layout: Overlay with Stack
        overlay = Gtk.Overlay()
        self.set_child(overlay)

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=300
        )
        overlay.set_child(self.stack)

        # Gear (settings) button
        gear = Gtk.Button()
        gear.set_icon_name("emblem-system-symbolic")
        gear.set_can_focus(False)
        gear.set_valign(Gtk.Align.START)
        gear.set_halign(Gtk.Align.END)
        gear.set_margin_top(4)
        gear.set_margin_end(4)
        gear.set_css_classes(["gear-button"])
        gear.connect("clicked", self.open_settings)
        overlay.add_overlay(gear)

        # Trash (delete) button
        trash = Gtk.Button()
        trash.set_icon_name("user-trash-symbolic")
        trash.set_can_focus(False)
        trash.set_valign(Gtk.Align.START)
        trash.set_halign(Gtk.Align.END)
        trash.set_margin_top(4)
        trash.set_margin_end(36)
        trash.set_css_classes(["trash-button"])
        trash.connect("clicked", self.delete_current_note)
        overlay.add_overlay(trash)

        # Dog-ear indicator
        self.dog_ear = Gtk.Button()
        self.dog_ear.set_can_focus(False)
        self.dog_ear.set_valign(Gtk.Align.END)
        self.dog_ear.set_halign(Gtk.Align.END)
        self.dog_ear.set_margin_bottom(4)
        self.dog_ear.set_margin_end(4)
        self.dog_ear.set_css_classes(["dog-ear-button"])
        self.dog_ear.connect("clicked", self.cycle_notes)
        self.dog_ear.set_visible(False)
        overlay.add_overlay(self.dog_ear)

        # Load persisted notes or create the first note
        if not self.load_notes():
            self.create_new_note("Note 1", "")

        # Keyboard shortcuts: Ctrl+S (stack), Ctrl+D (delete)
        sc = Gtk.ShortcutController()
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>s"),
            Gtk.CallbackAction.new(self.stack_note)
        ))
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>d"),
            Gtk.CallbackAction.new(self.delete_current_note)
        ))
        self.add_controller(sc)

        # Drag-to-move using GestureClick
        drag = Gtk.GestureClick()
        drag.set_button(1)
        drag.connect("pressed", self.on_drag_begin)
        self.stack.add_controller(drag)

        # Apply initial CSS styling
        self.apply_css()

    def get_font_fallbacks(self, primary_font):
        """Get a list of font fallbacks for better cross-distro compatibility"""
        fallbacks = [
            primary_font,
            "DejaVu Sans",
            "Liberation Sans",
            "Ubuntu",
            "Noto Sans",
            "sans-serif"
        ]
        return fallbacks

    def create_new_note(self, title, content=""):
        tv = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        tv.set_css_classes(["sticky-note-textview"])

        # Apply font directly to textview as backup
        try:
            desc = Pango.FontDescription(self.current_font)
            tv.override_font(desc)
        except:
            print(f"Warning: Could not apply font {self.current_font}")

        if content:
            buf = tv.get_buffer()
            buf.set_text(content)
        name = f"note_{len(self.note_stack)}"
        self.stack.add_named(tv, name)
        self.note_stack.append({'textview': tv, 'title': title, 'name': name})
        self.stack.set_visible_child_name(name)
        self.current_note_index = len(self.note_stack) - 1
        self.update_dog_ear_visibility()
        self.save_notes()
        return tv

    def stack_note(self, *_):
        self.note_counter += 1
        self.create_new_note(f"Note {self.note_counter}", "")
        self.update_dog_ear_visibility()
        return True

    def delete_current_note(self, *_):
        if not self.note_stack:
            return True
        note = self.note_stack.pop(self.current_note_index)
        child = self.stack.get_child_by_name(note['name'])
        if child:
            self.stack.remove(child)
        if self.current_note_index >= len(self.note_stack):
            self.current_note_index = len(self.note_stack) - 1
        if not self.note_stack:
            self.note_counter = 1
            self.create_new_note("Note 1", "")
        else:
            name = self.note_stack[self.current_note_index]['name']
            self.stack.set_visible_child_name(name)
        self.update_dog_ear_visibility()
        self.save_notes()
        return True

    def cycle_notes(self, *_):
        if len(self.note_stack) < 2:
            return
        self.current_note_index = (self.current_note_index + 1) % len(self.note_stack)
        name = self.note_stack[self.current_note_index]['name']
        self.stack.set_visible_child_name(name)
        self.update_dog_ear_visibility()

    def update_dog_ear_visibility(self):
        total = len(self.note_stack)
        current = self.current_note_index + 1
        visible = total > 1
        self.dog_ear.set_visible(visible)
        if visible:
            self.dog_ear.set_label(f"{current}/{total}")

    def apply_css(self):
        try:
            desc = Pango.FontDescription(self.current_font)
            family = desc.get_family()
            size = desc.get_size() // Pango.SCALE or 15

            if not family:
                family = "Sans"

        except Exception as e:
            print(f"Font parsing error: {e}")
            family = "Sans"
            size = 15

        # Create font fallback list
        font_fallbacks = self.get_font_fallbacks(family)
        font_list = ", ".join([f'"{font}"' for font in font_fallbacks])

        css = f"""
        /* Main window styling */
        .sticky-note-window {{
            background-color: {self.current_bg};
        }}

        /* TextView styling with font fallbacks */
        .sticky-note-textview {{
            background-color: {self.current_bg};
            color: {self.current_fg};
            font-family: {font_list};
            font-size: {size}px;
            padding: 8px;
            border: none;
        }}

        .sticky-note-textview text {{
            background-color: {self.current_bg};
            color: {self.current_fg};
            font-family: {font_list};
            font-size: {size}px;
        }}

        /* Button styling */
        .gear-button, .trash-button {{
            background-color: transparent;
            border: none;
            padding: 2px;
            color: {self.current_fg};
            min-width: 24px;
            min-height: 24px;
        }}

        .gear-button:hover, .trash-button:hover {{
            background-color: rgba(0,0,0,0.1);
            border-radius: 4px;
        }}

        /* Dog-ear button */
        .dog-ear-button {{
            background-color: rgba(0,0,0,0.1);
            border: none;
            padding: 4px 8px;
            border-radius: 8px 0 0 0;
            font-size: 12px;
            font-weight: bold;
            color: rgba(0,0,0,0.6);
            min-width: 32px;
            min-height: 24px;
        }}

        .dog-ear-button:hover {{
            background-color: rgba(0,0,0,0.15);
        }}
        """

        try:
            self.css.load_from_data(css.encode())
            print(f"CSS applied successfully with font: {family} {size}px")
        except Exception as e:
            print(f"CSS application error: {e}")

    def on_drag_begin(self, gesture, _, x, y):
        surf = self.get_surface()
        if surf and hasattr(surf, 'begin_move'):
            dev = gesture.get_device()
            seq = gesture.get_current_sequence()
            ev  = gesture.get_last_event(seq)
            if ev:
                surf.begin_move(dev, 1, x, y, ev.get_time())

    def open_settings(self, _):
        win = Gtk.Window(title="Settings", transient_for=self, modal=True)
        win.set_default_size(380, 300)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12,
                      margin_start=12, margin_end=12)

        # Font picker
        box.append(Gtk.Label(label="Font:", halign=Gtk.Align.START))
        fd = Gtk.FontDialog(title="Choose Font")
        fb = Gtk.FontDialogButton(dialog=fd)

        try:
            current_desc = Pango.FontDescription(self.current_font)
            fb.set_font_desc(current_desc)
        except:
            # Fallback to default font
            fb.set_font_desc(Pango.FontDescription("Sans 15"))

        fb.connect("notify::font-desc", self.on_font_changed)
        box.append(fb)

        # Text color picker
        box.append(Gtk.Label(label="Text Color:", halign=Gtk.Align.START))
        td = Gtk.ColorDialog(title="Choose Text Color")
        tb = Gtk.ColorDialogButton(dialog=td)
        rgba = Gdk.RGBA()
        rgba.parse(self.current_fg)
        tb.set_rgba(rgba)
        tb.connect("notify::rgba", self.on_text_color_changed)
        box.append(tb)

        # Background color picker
        box.append(Gtk.Label(label="Background Color:", halign=Gtk.Align.START))
        bd = Gtk.ColorDialog(title="Choose Background Color")
        bb = Gtk.ColorDialogButton(dialog=bd)
        rgba2 = Gdk.RGBA()
        rgba2.parse(self.current_bg)
        bb.set_rgba(rgba2)
        bb.connect("notify::rgba", self.on_bg_color_changed)
        box.append(bb)

        # Close button with proper styling reapplication
        close = Gtk.Button(label="Close")
        def on_close_clicked(*_):
            self.save_notes()
            self.save_prefs()
            self.apply_styling_to_all_notes()
            win.close()

        close.connect("clicked", on_close_clicked)
        box.append(close)

        win.set_child(box)
        win.present()

    def apply_styling_to_all_notes(self):
        """Apply current styling to all existing notes"""
        self.apply_css()

        # Apply font directly to each textview as backup
        try:
            desc = Pango.FontDescription(self.current_font)
            for note in self.note_stack:
                tv = note['textview']
                tv.override_font(desc)
                tv.set_css_classes(["sticky-note-textview"])
        except Exception as e:
            print(f"Error applying font to textviews: {e}")

    def on_font_changed(self, btn, _):
        desc = btn.get_font_desc()
        if desc:
            self.current_font = desc.to_string()
            print(f"Font changed to: {self.current_font}")
            self.apply_styling_to_all_notes()

    def on_text_color_changed(self, btn, _):
        rgba = btn.get_rgba()
        if rgba:
            self.current_fg = rgba.to_string()
            print(f"Text color changed to: {self.current_fg}")
            self.apply_styling_to_all_notes()

    def on_bg_color_changed(self, btn, _):
        rgba = btn.get_rgba()
        if rgba:
            self.current_bg = rgba.to_string()
            print(f"Background color changed to: {self.current_bg}")
            self.apply_styling_to_all_notes()

    def save_notes(self):
        notes = []
        for n in self.note_stack:
            buf = n['textview'].get_buffer()
            txt = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            notes.append({'title': n['title'], 'content': txt})
        try:
            full = json.load(open(self.data_file, 'r', encoding='utf-8')) if os.path.exists(self.data_file) else {}
        except:
            full = {}
        full['notes'] = notes
        # preserve prefs if present
        prefs = full.get('_prefs', {})
        full['_prefs'] = prefs
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(full, f, ensure_ascii=False, indent=2)

    def load_notes(self):
        if not os.path.isfile(self.data_file):
            return False
        try:
            data = json.load(open(self.data_file, 'r', encoding='utf-8'))
            for idx, entry in enumerate(data.get('notes', []), 1):
                self.note_counter = idx
                self.create_new_note(entry.get('title', f"Note {idx}"),
                                     entry.get('content', ""))
            return True
        except Exception as e:
            print(f"Error loading notes: {e}")
            return False

    def save_prefs(self):
        try:
            # Try to load existing data
            if os.path.isfile(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    full = json.load(f)
            else:
                full = {}

            # Update preferences
            full['_prefs'] = {
                'font': self.current_font,
                'fg':   self.current_fg,
                'bg':   self.current_bg
            }

            # Write back to file
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(full, f, ensure_ascii=False, indent=2)

            print(f"Preferences saved: font={self.current_font}, fg={self.current_fg}, bg={self.current_bg}")

        except Exception as e:
            print(f"Error saving preferences: {e}")

    def load_prefs(self):
        if not os.path.isfile(self.data_file):
            return
        try:
            full = json.load(open(self.data_file, 'r', encoding='utf-8'))
            prefs = full.get('_prefs', {})
            self.current_font = prefs.get('font', self.current_font)
            self.current_fg   = prefs.get('fg',   self.current_fg)
            self.current_bg   = prefs.get('bg',   self.current_bg)
            print(f"Preferences loaded: font={self.current_font}, fg={self.current_fg}, bg={self.current_bg}")
        except Exception as e:
            print(f"Error loading preferences: {e}")

def main():
    app = Gtk.Application(application_id="com.stickity.stacks")
    app.connect("activate", lambda a: (w := StickyNote()).set_application(a) or w.present())
    app.run([])

if __name__ == "__main__":
    main()
