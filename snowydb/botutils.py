from functools import wraps


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def restrict_to(users, on_unauthorized_access):
    def restricted(func):
        @wraps(func)
        def wrapped(bot, update, *args, **kwargs):
            user_id = update.effective_user.id
            if user_id not in users:
                on_unauthorized_access(bot, update)
                return
            return func(bot, update, *args, **kwargs)

        return wrapped

    return restricted


def strip_command(cmd):
    """Returns the command given stripping first part name and removing any first spaces

    '/echo test' -> 'test'
    """
    if cmd[0] != '/':
        return cmd.lstrip(' ')
    first_space = cmd.find(' ')
    if first_space == -1:
        return ''
    return cmd[first_space:].lstrip(' ')


def lookahead(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, True
        last = val
    # Report the last value.
    yield last, False


def edit_or_send(bot, update, text, reply_markup=None):
    if update.callback_query and update.callback_query.message.text:
        update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


VALID_DEEPLINK_CHARS = str.maketrans('', '', 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')


def is_valid_deeplink(s):
    return not str(s).translate(VALID_DEEPLINK_CHARS)
