import flet as ft
import asyncio
import edge_tts
import vlc
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def get_document_dir():
    return str(os.path.expanduser('~\Documents')) + '\pars\\'


def text_convert(text, rate, volume):
    VOICE = "tr-TR-AhmetNeural"
    # OUTPUT_FILE = "test.mp3" # temp > out

    async def generate_audio():
        communicate = edge_tts.Communicate(text, VOICE, rate=rate, volume=volume,)
        await communicate.save('text.mp3')
        sub = edge_tts.SubMaker()
        # with open('test.vtt', 'w', encoding='utf-8') as file:
        #     file.write(
        #         sub.generate_subs()
        #     )
    # Run the asynchronous function in a synchronous manner
    asyncio.run(generate_audio())

def listen_audio():
    global player

    instance = vlc.Instance("--no-xlib")
    # Player oluştur
    player = instance.media_player_new()
    # def play_audio():
    # MP3 dosyasını yükle
    media = instance.media_new('text.mp3')
    # Player'a medyayı ata
    player.set_media(media)
    # Player'ı başlat
    player.play()

    # asyncio.run(play_audio())
# def

def main(page: ft.Page):
    page.window_width = 850
    page.window_height = 300
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_center()


    volume_level_label = ft.Text('+40%')
    rate_speed_level_label = ft.Text('+20%')

    def update_volume_label(text: str):
        volume_level_label.value = text
        page.update()

    def update_rate_speed_label(text: str):
        rate_speed_level_label.value = text
        page.update()

    def volume_change(event):
        value = str(event.__dict__.get('data')).split('.')
        value[0] = value[0] + 1 if value[0] == 0 else value[0]
        value[0] = value[0] if value[0].startswith('-') else '+' + value[0]
        update_volume_label(f'{value[0]}%')

    def rate_speed_change(event):
        value = str(event.__dict__.get('data')).split('.')
        value[0] = value[0] + 1 if value[0] == 0 else value[0]
        value[0] = value[0] if value[0].startswith('-') else '+' + value[0]
        update_rate_speed_label(f'{value[0]}%')

    volume_bar = ft.Slider(min=-100, max=100, value=0, on_change=volume_change)
    rate_speed_bar = ft.Slider(min=-100, max=100, value=0, on_change=rate_speed_change)

    def ref_volume(e):
        volume_bar.value = 0
        update_volume_label('1%')

    def ref_rate_speed(e):
        rate_speed_bar.value = 0
        update_rate_speed_label('1%')

    volume_reset_button = ft.TextButton('Sıfırla', on_click=ref_volume)
    rate_speed_reset_button = ft.TextButton('Sıfırla', on_click=ref_rate_speed)

    text_input = ft.TextField(
        multiline=True,
    )
    text_area = ft.Container(
            content=text_input,
            alignment=ft.alignment.center,
        )

    volume = ft.Row(
        controls=[
            ft.Text('Ses Seviyesi'),
            volume_bar,
            volume_level_label,
            volume_reset_button
        ]
    )

    read_speed = ft.Row(
        controls=[
            ft.Text('Okuma Hızı'),
            rate_speed_bar,
            rate_speed_level_label,
            rate_speed_reset_button
        ]
    )

    def file_path_change(e):
        print(file_path.result.path)

    def get_new_file_path(e):
        file_path.get_directory_path()

    def listen_result(e) -> None:
        text_convert(
            text_input.value,
            rate_speed_level_label.value,
            volume_level_label.value
        )
        listen_audio()

    file_name_input = ft.TextField()
    file_path_label = ft.Text(get_document_dir())

    def save_audio(e):
        global player
        if player.get_state() != vlc.State.Ended:
            player.stop()
        player.release()
        text_convert(
            text_input.value,
            rate_speed_level_label.value,
            volume_level_label.value
        )
        name = file_name_input.value if file_name_input.value else 'noname.mp3'
        file_path = file_path_label.value
        os.replace('text.mp3', f'{file_path}{name}.mp3')

    def stop_audio(e):
        global player
        if player.get_state() != vlc.State.Ended:
            player.stop()
            player.release()

    def set_new_file_name(e):
        t = file_path.result.path + '\\'
        file_path_label.value = t
        page.update()

    file_path = ft.FilePicker(on_result=set_new_file_name)

    read_button = ft.TextButton('Dinle', on_click=listen_result)
    get_path_button = ft.TextButton('Gözat', on_click=get_new_file_path)
    save_button = ft.TextButton('Kaydet', on_click=save_audio)
    stop_button = ft.TextButton('Durdur', on_click=stop_audio)

    control_bar = ft.Row(
        controls=[
            file_path_label,
            file_name_input,
            get_path_button,
            save_button,
            read_button,
            stop_button
        ]
    )

    page.add(
        ft.Column(spacing=0, controls=[
            text_area,
            volume,
            read_speed,
            control_bar,
            file_path
        ])
    )


if __name__ == '__main__':
    ft.app(target=main)

