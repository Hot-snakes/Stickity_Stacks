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
        # Default style values
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

    def create_new_note(self, title, content=""):
        tv = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        tv.set_css_classes(["sticky-note"])
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
            fam  = desc.get_family()
            sz   = desc.get_size() // Pango.SCALE or 15
        except:
            fam = "Sans"
            sz = 15

        css = f"""
.sticky-note-window .sticky-note textview {{
    background-color: {self.current_bg};
    color: {self.current_fg};
    font-family: "{fam}";
    font-size: {sz}px;
}}
.sticky-note-window .sticky-note text {{
    color: {self.current_fg};
}}
.gear-button, .trash-button {{
    background-color: transparent;
    border: none;
    padding: 2px;
    color: {self.current_fg};
}}
.dog-ear-button {{
    background-color: rgba(0,0,0,0.1);
    border: none;
    padding: 4px 8px;
    border-radius: 8px 0 0 0;
    font-size: 12px;
    font-weight: bold;
    color: rgba(0,0,0,0.6);
    /* Note: box-shadow is not supported in GTK CSS, so you may remove or adjust this property if you get errors. */
}}
.dog-ear-button:hover {{
    background-color: rgba(0,0,0,0.15);
}}
"""
        self.css.load_from_data(css.encode())

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
        fb.set_font_desc(Pango.FontDescription(self.current_font))
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
            # Force reapply CSS after closing settings
            self.apply_css()
            # Also reapply CSS classes to all textviews
            for note in self.note_stack:
                note['textview'].set_css_classes(["sticky-note"])
            win.close()
        
        close.connect("clicked", on_close_clicked)
        box.append(close)

        win.set_child(box)
        win.present()

    def on_font_changed(self, btn, _):
        desc = btn.get_font_desc()
        if desc:
            self.current_font = desc.to_string()
            self.apply_css()
            for note in self.note_stack:
                note['textview'].set_css_classes(["sticky-note"])

    def on_text_color_changed(self, btn, _):
        rgba = btn.get_rgba()
        if rgba:
            self.current_fg = rgba.to_string()
            self.apply_css()

    def on_bg_color_changed(self, btn, _):
        rgba = btn.get_rgba()
        if rgba:
            self.current_bg = rgba.to_string()
            self.apply_css()

    def save_notes(self):
        notes = []
        for n in self.note_stack:
            buf = n['textview'].get_buffer()
            txt = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            notes.append({'title': n['title'], 'content': txt})
        try:
            full = json.load(open(self.data_file, 'r', encoding='utf-8'))
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
        except:
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
        except:
            pass

def main():
    app = Gtk.Application(application_id="com.stickity.stacks")
    app.connect("activate", lambda a: (w := StickyNote()).set_application(a) or w.present())
    app.run([])

if __name__ == "__main__":
    main()
