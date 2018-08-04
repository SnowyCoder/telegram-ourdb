from telegram import Update, CallbackQuery
from telegram.ext.handler import Handler


class CallbackCommandHandler(Handler):
    """
        Handler class to handle Telegram callback queries. Optionally based on a regex.
        Read the documentation of the ``re`` module for more information.

        Attributes:
            cmd_char (:obj:`str`): The single-char prefix that will trigger this callback
            callback (:obj:`callable`): The callback function for this handler.
            pass_data (:obj:`bool`): Optional. Determines whether the remaining callback data will be
                passed to the callback function.
            auto_answer_query (:obj:`bool`): Optional. Determines whether this handler will answer the query
                automatically (disable if you want to customize the query response)
            pass_update_queue (:obj:`bool`): Optional. Determines whether ``update_queue`` will be
                passed to the callback function.
            pass_job_queue (:obj:`bool`): Optional. Determines whether ``job_queue`` will be passed to
                the callback function.
            pass_user_data (:obj:`bool`): Optional. Determines whether ``user_data`` will be passed to
                the callback function.
            pass_chat_data (:obj:`bool`): Optional. Determines whether ``chat_data`` will be passed to
                the callback function.

        Note:
            :attr:`pass_user_data` and :attr:`pass_chat_data` determine whether a ``dict`` you
            can use to keep any data in will be sent to the :attr:`callback` function.. Related to
            either the user or the chat that the update was sent in. For each update from the same user
            or in the same chat, it will be the same ``dict``.

        Args:
            callback (:obj:`callable`): A function that takes ``bot, update`` as positional arguments.
                It will be called when the :attr:`check_update` has determined that an update should be
                processed by this handler.
            pass_data (:obj:`bool`, optional): Determines whether the remaining callback data will be
                passed to the callback function. Default is ``False``
            auto_answer_query (:obj:`bool`, optional): Determines whether this handler will answer the query
                automatically (disable if you want to customize the query response). Default is ``True``
            pass_update_queue (:obj:`bool`, optional): If set to ``True``, a keyword argument called
                ``update_queue`` will be passed to the callback function. It will be the ``Queue``
                instance used by the :class:`telegram.ext.Updater` and :class:`telegram.ext.Dispatcher`
                that contains new updates which can be used to insert updates. Default is ``False``.
            pass_job_queue (:obj:`bool`, optional): If set to ``True``, a keyword argument called
                ``job_queue`` will be passed to the callback function. It will be a
                :class:`telegram.ext.JobQueue` instance created by the :class:`telegram.ext.Updater`
                which can be used to schedule new jobs. Default is ``False``.
            pass_user_data (:obj:`bool`, optional): If set to ``True``, a keyword argument called
                ``user_data`` will be passed to the callback function. Default is ``False``.
            pass_chat_data (:obj:`bool`, optional): If set to ``True``, a keyword argument called
                ``chat_data`` will be passed to the callback function. Default is ``False``.
        """

    def __init__(self, cmd_char: str, callback, pass_data=False, auto_answer_query=True, **kwargs):
        super().__init__(callback, **kwargs)

        self.cmd_char = cmd_char
        self.callback = callback
        self.pass_data = pass_data
        self.auto_answer_query = auto_answer_query

        self.next_data = None

    def check_data(self, data):
        if data[0] == self.cmd_char:
            self.next_data = data[1:]
            return True
        return False

    def check_update(self, update):
        """
        Determines whether an update should be passed to this handlers :attr:`callback`.

        Args:
            update (:class:`telegram.Update`): Incoming telegram update.

        Returns:
            :obj:`bool`
        """
        if not (isinstance(update, Update) and update.callback_query):
            return

        data = update.callback_query.data

        if not data:
            return False
        return self.check_data(data)

    def handle_update(self, update, dispatcher):
        """
        Send the update to the :attr:`callback`.

        Args:
            update (:class:`telegram.Update`): Incoming telegram update.
            dispatcher (:class:`telegram.ext.Dispatcher`): Dispatcher that originated the Update.
        """

        if self.auto_answer_query:
            update.callback_query.answer()

        kwargs = self.collect_optional_args(dispatcher, update)
        args = [dispatcher.bot, update]

        if self.pass_data:
            args.append(self.next_data)

        res = self.callback(*args, **kwargs)

        return res
