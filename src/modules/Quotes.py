import random
import threading

import gspread

import src.models as models
import src.modules.Utils as Utils


class QuotesMixin:
    @Utils._retry_gspread_func
    @Utils._mod_only
    def update_quote_spreadsheet(self, db_session):
        """
        Updates the quote spreadsheet from the database.
        Only call directly if you really need to as the bot
        won't be able to do anything else while updating.

        !update_quote_spreadsheet
        """
        spreadsheet_name, web_view_link = self.spreadsheets['quotes']
        gc = gspread.authorize(self.credentials)
        sheet = gc.open(spreadsheet_name)
        qs = sheet.worksheet('Quotes')

        quotes = db_session.query(models.Quote).all()

        for index in range(len(quotes) + 10):
            qs.update_cell(index + 2, 1, '')
            qs.update_cell(index + 2, 2, '')

        for index, quote_obj in enumerate(quotes):
            qs.update_cell(index + 2, 1, index + 1)
            qs.update_cell(index + 2, 2, quote_obj.quote)

    @Utils._mod_only
    def update_quote_db_from_spreadsheet(self, db_session):
        """
        Updates the database from the quote spreadsheet.
        Only call directly if you really need to as the bot
        won't be able to do anything else while updating.
        This function will stop looking for quotes when it
        finds an empty row in the spreadsheet.

        !update_quote_db_from_spreadsheet
        """
        spreadsheet_name, web_view_link = self.spreadsheets['quotes']
        gc = gspread.authorize(self.credentials)
        sheet = gc.open(spreadsheet_name)
        qs = sheet.worksheet('Quotes')
        cell_location = [2, 2]
        quotes_list = []
        while True:
            if bool(qs.cell(*cell_location).value) is not False:
                quotes_list.append(models.Quote(quote=qs.cell(*cell_location).value))
                cell_location[0] += 1
            else:
                break

        db_session.execute(
            "DELETE FROM QUOTES;"
        )
        db_session.add_all(quotes_list)

    def add_quote(self, message, db_session):
        """
        Adds a quote to the database.

        !add_quote Oh look, the caster has uttered an innuendo!
        """
        msg_list = self.service.get_message_content(message).split(' ')
        quote_str = ' '.join(msg_list[1:])
        response_str = self._add_quote(db_session, quote_str)
        self._add_to_chat_queue(response_str)

    @Utils._mod_only
    def edit_quote(self, message, db_session):
        """
        Edits a user created quote. 
        Takes a 1 indexed quote index. 
        
        !edit_quote 5 This quote is now different
        """
        msg_list = self.service.get_message_content(message).split(' ')
        if len(msg_list) > 1 and msg_list[1].isdigit() and int(msg_list[1]) > 0:
            quote_id = int(msg_list[1])
            quote_str = ' '.join(msg_list[2:])
            response_str = self._edit_quote(db_session, quote_id, quote_str)
            self._add_to_chat_queue(response_str)
        else:
            self._add_to_chat_queue('You must use a digit to specify a quote.')

    @Utils._mod_only
    def delete_quote(self, message, db_session):
        """
        Removes a user created quote.
        Takes a 1 indexed quote index.

        !delete_quote 5
        """
        msg_list = self.service.get_message_content(message).split(' ')
        if len(msg_list) > 1 and msg_list[1].isdigit() and int(msg_list[1]) > 0:
            quote_id = int(msg_list[1])
            response_str = self._delete_quote(db_session, quote_id)
            self._add_to_chat_queue(response_str)

    def show_quotes(self):
        """
        Links to the google spreadsheet containing all the quotes.

        !show_quotes
        """
        web_view_link = self.spreadsheets['quotes'][1]
        short_url = self.shortener.short(web_view_link)
        self._add_to_chat_queue('View the quotes at: {}'.format(short_url))

    def quote(self, message, db_session):
        """
        Displays a quote in chat. Takes a 1 indexed quote index.
        If no index is specified, displays a random quote.
        
        !quote
        !quote 5
        !quote add Oh look, the caster has uttered an innuendo!
        !quote edit 5 This quote is now different
        !quote delete 5
        """
        msg_list = self.service.get_message_content(message).split(' ')
        if len(msg_list) == 1:  # !quote
            quote_str = self._get_random_quote(db_session)
            self._add_to_chat_queue(quote_str)
        elif msg_list[1].isdigit():  # !quote 50
            quote_id = int(msg_list[1])
            quote_str = self._get_quote(db_session, quote_id)
            self._add_to_chat_queue(quote_str)
        else:  # !quote add/edit/delete
            action = msg_list[1].lower()
            if action == 'add':  # !quote add Oh look, the caster has uttered an innuendo!
                quote_str = ' '.join(msg_list[2:])
                response_str = self._add_quote(db_session, quote_str)
                self._add_to_chat_queue(response_str)
            elif action == 'edit':  # !quote edit 5 This quote is now different
                if self.service.get_mod_status(message):
                    quote_id = int(msg_list[2])
                    quote_str = ' '.join(msg_list[3:])
                    response_str = self._edit_quote(db_session, quote_id, quote_str)
                    self._add_to_chat_queue(response_str)
            elif action == 'delete':  # !quote delete 5
                if self.service.get_mod_status(message):
                    quote_id = int(msg_list[2])
                    response_str = self._delete_quote(db_session, quote_id)
                    self._add_to_chat_queue(response_str)

    def _get_quote(self, db_session, quote_id):
        # We grab all the quotes because we can't just use the quote ID
        # Quotes may get deleted, and so we need to set all quotes after that one back by one
        quote_objs = db_session.query(models.Quote).all()
        if quote_id <= len(quote_objs):
            quote_obj = quote_objs[quote_id-1]
            response_str = f'#{quote_obj.id} {quote_obj.quote}'
        else:
            response_str = f'Invalid quote id - there are only {len(quote_objs)} quotes'
        return response_str

    def _get_random_quote(self, db_session):
        quote_ob_list = db_session.query(models.Quote).all()
        if len(quote_ob_list) > 0:
            quote_obj = random.choice(quote_ob_list)
            response_str = f'#{quote_obj.id} {quote_obj.quote}'
        else:
            response_str = 'No quotes currently exist'
        return response_str

    def _add_quote(self, db_session, quote_str):
        quote_obj = models.Quote(quote=quote_str)
        db_session.add(quote_obj)
        response_str = f'Quote added as quote #{db_session.query(models.Quote).count()}.'

        # Replace this bit using the command queue
        my_thread = threading.Thread(target=self.update_quote_spreadsheet,
                                     kwargs={'db_session': db_session})
        my_thread.daemon = True
        my_thread.start()

        return response_str

    def _edit_quote(self, db_session, quote_id, quote_str):
        # We grab all the quotes because we can't just use the quote ID
        # Quotes may get deleted, and so we need to set all quotes after that one back by one
        quote_objs = db_session.query(models.Quote).all()
        if quote_id <= len(quote_objs):
            quote_obj = quote_objs[quote_id - 1]
            quote_obj.quote = quote_str
            response_str = 'Quote has been edited.'
            my_thread = threading.Thread(target=self.update_quote_spreadsheet,
                                         kwargs={'db_session': db_session})
            my_thread.daemon = True
            my_thread.start()
        else:
            response_str = 'That quote does not exist'
        return response_str

    def _delete_quote(self, db_session, quote_id):
        # We grab all the quotes because we can't just use the quote ID
        # Quotes may get deleted, and so we need to set all quotes after that one back by one
        quote_objs = db_session.query(models.Quote).all()
        if quote_id <= len(quote_objs):
            quote_obj = quote_objs[quote_id - 1]
            db_session.delete(quote_obj)
            response_str = 'Quote deleted'
            my_thread = threading.Thread(target=self.update_quote_spreadsheet,
                                         kwargs={'db_session': db_session})
            my_thread.daemon = True
            my_thread.start()
        else:
            response_str = 'That quote does not exist'
        return response_str
