from .addon import install

if __name__=='__main__':
    install()
    from shortsflow import webui
    webui.main()
