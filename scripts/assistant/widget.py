import gradio as gr


# After the Gradio v3.40.0+, the constructor signature changes, in order to keep backward compatibility,
# we use try...catch syntax to archive this purpose.

def Dataset(**kwargs) -> gr.Dataset:
    try:
        return gr.Dataset(**kwargs)
    except:
        constructor_args = {}
        style_args = {}

        for k, v in kwargs.items():
            if k == "elem_classes":
                style_args["type"] = v
            elif k == "container":
                style_args["container"] = v
            else:
                constructor_args[k] = v
        return gr.Dataset(**constructor_args).style(**style_args)


def Row(**kwargs) -> gr.Row:
    try:
        return gr.Row(**kwargs)
    except:
        return gr.Row().style(**kwargs)


def Dropdown(**kwargs) -> gr.Dropdown:
    try:
        return gr.Dropdown(**kwargs)
    except:
        constructor_args = {}
        style_args = {}

        for k, v in kwargs.items():
            if k == "show_progress":
                style_args["full_width"] = v == "full"
            else:
                constructor_args[k] = v

        return gr.Dropdown(**constructor_args).style(**style_args)


def Radio(**kwargs) -> gr.Radio:
    try:
        return gr.Radio(**kwargs)
    except:
        constructor_args = {}
        style_args = {}

        for k, v in kwargs.items():
            if k == "elem_classes":
                style_args["full_width"] = v == "full"
            else:
                constructor_args[k] = v

        return gr.Radio(**constructor_args).style(**style_args)