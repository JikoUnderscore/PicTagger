import os
import sys
import exiftool
import tkinter as tk
import inspect
import PIL.ImageTk, PIL.Image, PIL.Image, PIL.ImageFile
import subprocess

PIL.ImageFile.LOAD_TRUNCATED_IMAGES = True

class IndexJpg:
    __slots__ = ["index"]
    def __init__(self, index:int) -> None:
        self.index = index

class TagRow:
    __slots__ = ["row"]
    def __init__(self, col:int) -> None:
        self.row = col




def debug(var):
    frame = inspect.currentframe().f_back # pyright: ignore
    var_name = None
    for name, value in frame.f_locals.items(): # pyright: ignore
        if value is var:
            var_name = name
            break
    print(f"{var_name}={var!r}")



def list_files_in_directory(directory: str) -> list[str]:
    jpg_files: list[str] = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_file():
                    name = entry.name.lower()
                    if name.endswith((".jpg", ".jpeg")) or name.endswith(".png"):
                        jpg_files.append(entry.path.strip())
    except FileNotFoundError:
        print(f"🛑 The directory '{directory}' does not exist.")
    except NotADirectoryError:
        print(f"🛑 The path '{directory}' is not a directory.")
    except PermissionError:
        print(f"🛑 Permission denied for accessing the directory '{directory}'.")

    return jpg_files


def extract_and_correct_metadata(file_path: str) -> list[str]:
    print(f"{file_path=}")
    result = subprocess.run(["exiftool", "-charset", "filename=utf8", file_path], capture_output=True, text=True) # , encoding="utf-8"
    raw_metadata = result.stdout
    
    # Step 2: Correct encoding of each metadata field
    # corrected_metadata = {}
    for line in raw_metadata.splitlines():
        if ': ' in line:
            key, value = line.split(': ', 1)
            if "Keyword" in key:
                # print(f"{line=}")
                # print(f"{value=}")
                split = value.split(",")
                data = [s.strip() for s in split]
                # print(f"{data=}")
                return data
    return []



def get_tags(et: exiftool.ExifToolHelper, file: str) -> list[str]:
    metadata = et.get_tags(file, None)
    for meta in metadata:
        meta: dict
        EXIF_XPKeywords: str | None = meta.get('EXIF:XPKeywords')
        IPTC_Keywords: list[str] | None | str = meta.get('IPTC:Keywords')
        

        match (EXIF_XPKeywords, IPTC_Keywords):
            case (str() as keyword, None) | (str() as keyword, _):
                encoded_bytes = keyword.encode('windows-1251')
                corrected_keywr = encoded_bytes.decode('utf-8')
                return corrected_keywr.split(";")
            case (None, list() as  keywordlist):
                keywordlist: list[str]
                if any("?" in s for s in keywordlist):
                    return extract_and_correct_metadata(file)
                else:
                    tagbuilder: list[str] = []
                    for keyword in keywordlist:
                        encoded_bytes = keyword.encode('windows-1251')
                        corrected_keywr = encoded_bytes.decode('utf-8')
                        tagbuilder.append(corrected_keywr)
                    return tagbuilder
            case (_, str() as keyword):
                if "?" in keyword:
                    return extract_and_correct_metadata(file)
                else:
                    encoded_bytes = keyword.encode('windows-1251')
                    corrected_keywr = encoded_bytes.decode('utf-8')
                    return corrected_keywr.split(";")
            case _:
                print("no tags")
                break
            

    return []


CURRENT_IMAGE: PIL.ImageTk.PhotoImage
CURRENT_TAGS: list[str] = []
CURRENT_FILEPATH: str = ""

def main():
    global CURRENT_IMAGE
    if len(sys.argv) < 2:
        print("🛑 Usage: python script.py <directory> [start index]")
        return 1
    jpg_files = list_files_in_directory(sys.argv[1])

    files_index = IndexJpg(int(sys.argv[2])) if len(sys.argv) == 3 else IndexJpg(0)

    root = tk.Tk()
    root.title("Pic tag now!")
    
    file = jpg_files[files_index.index]

    resized_image = resize_image(PIL.Image.open(file), 1280, 720)
    CURRENT_IMAGE  = PIL.ImageTk.PhotoImage(resized_image)


    tag_buttons: dict[str, tk.Button] = {}
    tab_buttons_rows = TagRow(0)

    listbox_tags = tk.Listbox(root)
    listbox_tags.grid(row=0, column=6)

    entry_item = tk.StringVar()
    entry = tk.Entry(root, textvariable=entry_item, width=20)
    entry.grid(row=1, column=3)

    buttons_frame = tk.Frame(root )
    buttons_frame.grid(row=0, column=7)



    with exiftool.ExifToolHelper() as et:
        entry.bind('<Return>', lambda e: entry_add_new_button(e, entry_item, tag_buttons, tab_buttons_rows, buttons_frame, listbox_tags, file))

        # tags = get_tags(et, file)
        # debug(tags)
        img_lbl = tk.Label(root, image=CURRENT_IMAGE) # type: ignore
        img_lbl.grid(row=0, column=0, columnspan=5)


        backward = tk.Button(root, text="<<", command=lambda: go_back(img_lbl, files_index, jpg_files, et, listbox_tags, tag_buttons, tab_buttons_rows,buttons_frame))
        forward = tk.Button(root, text=">>", command=lambda : go_forward(img_lbl, files_index, jpg_files, et, listbox_tags, tag_buttons, tab_buttons_rows,buttons_frame))
        
        backward.grid(row=1, column=0)
        forward.grid(row=1, column=1)


        # with exiftool.ExifToolHelper() as et:
        #     tags = get_tags(et)
        #     tags.extend(("novo", "широко"))
        #     debug(tags)
        #     et.set_tags("ex.jpg",tags={"Keywords": tags} , params=["-P", "-overwrite_original"]) # 
        root.bind('<space>', lambda _: go_forward(img_lbl, files_index, jpg_files, et, listbox_tags, tag_buttons, tab_buttons_rows,buttons_frame))
        go_back(img_lbl, files_index, jpg_files, et, listbox_tags, tag_buttons, tab_buttons_rows,buttons_frame)
        root.mainloop()


def add_button_tag(tagname: str, tag_buttons: dict[str, tk.Button], tab_buttons_rows: TagRow, buttons_frame: tk.Frame, listbox_tags: tk.Listbox):
    if tagname not in tag_buttons:
        button = tk.Button(buttons_frame, text=tagname)
        button.grid(row=tab_buttons_rows.row, column=0)
        tag_buttons[tagname] = button 
        button.config(command=lambda : button_do_stuff(listbox_tags, button['text']))
        tab_buttons_rows.row += 1


def entry_add_new_button(event, entry_item: tk.StringVar, tag_buttons: dict[str, tk.Button], tab_buttons_rows: TagRow, buttons_frame: tk.Frame, listbox_tags: tk.Listbox, file: str):
    value = entry_item.get()
    print(value)
    add_button_tag(value, tag_buttons, tab_buttons_rows, buttons_frame, listbox_tags)


def button_do_stuff( listbox_tags: tk.Listbox, button_text: str):
    global CURRENT_TAGS, CURRENT_FILEPATH

    keywords_to_remove: list[str] = []

    print(CURRENT_FILEPATH)
    print(button_text)

    if button_text in CURRENT_TAGS:
        # print("== REMOVEING ", CURRENT_FILEPATH)
        data: tuple[str, ...] = listbox_tags.get(0, tk.END)
        newdata: list[str] = []
        for dat in data:
            if dat == button_text:
                keywords_to_remove.append(dat)
                continue
            newdata.append(dat)
        listbox_tags.delete(0, tk.END)
        listbox_tags.insert(0, *newdata)
        CURRENT_TAGS = newdata
    else:
        # print("== ADDING ", CURRENT_FILEPATH)
        listbox_tags.insert(tk.END, button_text)
        CURRENT_TAGS.append(button_text)

    command = ["exiftool", "-P", "-overwrite_original"] # windows-1251 utf8 , 

    with open("args.txt", "w", encoding="utf8") as f:
        for tag in CURRENT_TAGS:
            f.write(f"-keywords={tag}\n")
        for remove_tag in keywords_to_remove:
            f.write(f"-keywords-={remove_tag}\n")

    command.extend(["-charset", "utf8", "-charset", "iptc=utf8", "-charset", "exif=utf8", "-charset", "filename=utf8" , "-codedcharacterset=utf8", "-@", "args.txt"])
    command.append(CURRENT_FILEPATH.strip()) # 
    # >exiftool -P -overwrite_original -charset utf8 -charset iptc=utf8 -charset exif=utf8 -charset filename=utf8 -codedcharacterset=utf8 -@ args.txt C:\\Users\\Underscore\\OneDrive\\Pictures\\cloud\\familija\\zhivotni\\007.jpg
    print(f"running commad {command=}")
    result = subprocess.run(command, capture_output=True, text=True)  # , encoding="utf-8"
    print("==================")
    print(result)
    print("=========DONE=========")

    # et.set_tags(CURRENT_FILEPATH, tags={"Keywords": CURRENT_TAGS} , params=params)
    # et.run()


def go_back(lable: tk.Label, index: IndexJpg, jpg_files: list[str], et: exiftool.ExifToolHelper, listbox_tags: tk.Listbox, tag_buttons: dict[str, tk.Button], tab_buttons_rows: TagRow, buttons_frame: tk.Frame):
    global CURRENT_IMAGE, CURRENT_TAGS, CURRENT_FILEPATH
    lable.grid_forget()
    
    new_index = index.index-1 if index.index >= 1 else 0
    CURRENT_FILEPATH = jpg_files[new_index]
    CURRENT_TAGS = get_tags(et, CURRENT_FILEPATH)

    print(CURRENT_FILEPATH)
    print(CURRENT_TAGS)
    listbox_tags.delete(0, tk.END)
    for item in CURRENT_TAGS:
        listbox_tags.insert(tk.END, item)
        add_button_tag(item, tag_buttons, tab_buttons_rows, buttons_frame, listbox_tags)


    resized_image = resize_image(PIL.Image.open(CURRENT_FILEPATH), 1280, 720)
    CURRENT_IMAGE  = PIL.ImageTk.PhotoImage(resized_image)
    
    lable = tk.Label(image=CURRENT_IMAGE) # type: ignore
    lable.grid(row=0, column=0, columnspan=5)
    index.index = new_index


def go_forward(lable: tk.Label,  index: IndexJpg, jpg_files: list[str], et: exiftool.ExifToolHelper, listbox_tags: tk.Listbox, tag_buttons: dict[str, tk.Button], tab_buttons_rows: TagRow, buttons_frame: tk.Frame):
    global CURRENT_IMAGE, CURRENT_TAGS, CURRENT_FILEPATH
    lable.grid_forget()
    
    new_index = index.index+1 if index.index+1 < len(jpg_files) else index.index
    CURRENT_FILEPATH = jpg_files[new_index]
    CURRENT_TAGS = get_tags(et, CURRENT_FILEPATH)

    print(CURRENT_FILEPATH)
    print(CURRENT_TAGS)
    print(f"INDEX {index.index}")
    listbox_tags.delete(0, tk.END)
    for item in CURRENT_TAGS:
        listbox_tags.insert(tk.END, item)
        add_button_tag(item, tag_buttons, tab_buttons_rows, buttons_frame, listbox_tags)


    resized_image = resize_image(PIL.Image.open(CURRENT_FILEPATH), 1280, 720)
    CURRENT_IMAGE  = PIL.ImageTk.PhotoImage(resized_image)
    
    lable = tk.Label(image=CURRENT_IMAGE) # type: ignore
    lable.grid(row=0, column=0, columnspan=5)
    index.index = new_index




def resize_image(image: PIL.Image.Image, max_width: int, max_height: int):
    width, height = image.size
    if width > max_width or height > max_height:
        ratio = min(max_width / width, max_height / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        return image.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)
    return image




if __name__ == "__main__":
    main()