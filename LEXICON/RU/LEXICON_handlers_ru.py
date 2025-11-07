# AUTO-GENERATED — do not edit

LEXICON_HANDLERS_RU = {

# ==ADMIN==

    "admin":{
    # FSM: Назначение нового регистратора
    "process_new_registrator": (
        "Пожалуйста, введите телеграм-ID участника,\n"
        "которому вы хотите присвоить новый статус или отправьте контакт с ID"
    ),
    "process_registrator_id_sent&no_text": "Произошла ошибка. Пожалуйста, отправьте корректный ID.",
    "process_registrator_contact_sent&no_contact": "Произошла ошибка. Пожалуйста, отправьте корректный контакт.",
    "process_registrator_id_sent&no_member_id": "Пользователь не найден",
    "process_registrator_profile_not_found": "Данные пользователя не найдены",

    # Подтверждение назначения регистратора (шаблон с {user_info})
    "confirm_new_registrator": (
        "Данные участника, которого вы назначаете регистратором:\n"
        "{user_info}\n"
        "Всё верно?"
    ),


    # FSM регистратора
    "failed_to_get_participant_id": "Не удалось получить ID участника.",
    "error_during_registrator_assignment": "Произошла ошибка: {ans_str}",

    "registrator_invitation_message": (
        "Здравствуйте! Администрация группы назначила вас регистратором.\n"
        "Это означает, что вам будут приходить заявки на вступления в группу, "
        "которые вы можете подтверждать или игнорировать.\n"
        'Если вы согласны на роль Регистратора, нажмите кнопку "Согласен".\n'
        'Если не согласны - кнопку "Не согласен"'
    ),
    "registrator_added_success": (
        "Спасибо! Кандидат в Регистраторы добавлен!\n"
        "Результат отправки сообщения кандидату:\n{response}\n"
        "Вы вышли из машины состояний"
    ),
    "registrator_not_added": (
        "Спасибо! Регистратор не добавлен!\n"
        "Попробуйте еще раз.\n"
        "Вы вышли из машины состояний"
    ),
    "use_buttons_or_cancel": (
        "Пожалуйста, воспользуйтесь кнопками!\n"
        "Если вы хотите прервать назначение регистратора - отправьте команду /cancel"
    ),

    # Список регистраторов
    "error_loading_registrators": "Произошла ошибка при формировании списка регистраторов. Попробуйте снова.",
    "no_registrators": "В данный момент нет регистраторов.",
    "registrator_card": "Регистратор: {username} {first_name} {last_name}",
    "super_registrator_card": "Суперегистратор: {username} {first_name} {last_name}",
    "back_to_main_menu": "Вернуться в основное меню",

    # Управление регистраторами
    "generic_error_try_again": "Произошла ошибка. Пожалуйста, попробуйте снова.",
    "error_removing_registrator": "Произошла ошибка при удалении регистратора.",
    "error_promoting_to_super": "Произошла ошибка при назначении суперрегистратора.",
    "error_removing_superregistrator": "Произошла ошибка при удалении суперрегистратора.",

    # Голосования
    "voting_not_from_your_group": "❌ Голосование не из вашей группы.",
    "unknown_voting_status": "Неизвестный статус голосования, обратитесь к администрации.",
    "choose_action": "Выберите действие",
    "unknown_error": "Неизвестная ошибка.",
    "error_starting_voting": "Произошла ошибка при запуске голосования.",
    "error_intermediate_voting_results": "Произошла ошибка при подведении промежуточного итога голосования.",
    "error_completing_voting": "Произошла ошибка при завершении голосования.",
    "error_deleting_variant": "Произошла ошибка при удалении варианта.",
    "unexpected_error_finishing_confirmation": "Произошла непредвиденная ошибка при завершении утверждения голосования.",
    "error_finishing_confirmation": "Произошла ошибка при завершении утверждения голосования.",

    # Бан
    "ban_enter_user_id_or_contact": (
        "Пожалуйста, введите телеграм-ID участника,\n"
        "которого вы хотите забанить или отправьте контакт с ID"
    ),
    "invalid_numeric_input": "Пожалуйста, введите корректное числовое значение.",
    "message_has_no_text": "Сообщение не содержит текст. Пожалуйста, попробуйте снова.",
    "ban_confirm_user_data": (
        "Данные участника которому вы хотите забанить:\n"
        "Имя: {first_name},\n"
        "    Фамилия: {last_name}, \n"
        " Телефон: {tg_phone_number}\n"
        "    Псевдоним: {username} Всё верно?"
    ),
    "user_profile_not_found": "Данные участника не найдены",
    "user_not_found_in_group": "Такой участник не найден",
    "error_message": "Произошла ошибка: {err}",
    "please_send_contact": "Пожалуйста, отправьте контакт.",
    "contact_has_no_id": "К сожалению, ID контакта отсутствует. Попробуйте отправить просто ID",
    "choose_ban_period_or_cancel": (
        "Выберите, какой срок бана вы хотите назначить. \n"
        "Если хотите прервать процедуру - наберите /cancel"
    ),
    "ban_cancelled": (
        "Спасибо! Новый бан не добавлен!\n"
        "Попробуйте еще раз.\n"
        "Вы вышли из машины состояний"
    ),
    "use_buttons_or_cancel_ban": (
        "Пожалуйста, воспользуйтесь кнопками!\n"
        "Если вы хотите прервать выставление бана - отправьте команду /cancel"
    ),
    "ban_button_not_a_number": "Нажатая кнопка не является числом. Сообщите администратору",
    "failed_to_get_user_id_for_ban": "❌ Не удалось получить ID участника.",
    "user_banned_for_days": "Участник забанен на {ban_time_days} дней",

    # Экспорт
    "choose_member_status_for_export": "Выберите, с каким статусом участников вы хотите выгрузить список:",
    "main_menu": "Главное меню:",
    "export_members_start": "Экспортировать список участников",
    "export_failed": "Не удалось экспортировать список участников.",

    # Рассылки
    "choose_mailing_audience": "Выберите, кому рассылать:",
    "enter_user_id_or_contact_for_mailing": "Введите телеграм ID пользователя или пришлите его контакт",
    "message_too_long_max_4000": "Сообщение слишком длинное (макс. 4000 символов). Попробуйте снова",
    },

# == ALL USERS ==

    "all_users": {
        "add_option": 'Добавить вариант',
        "admin_voting": 'Администрирование голосования',
        "admin_voting_1": 'Администрирование голосования',
        "admin_voting_2": 'Администрирование голосования',
        "all_valid_votes_in_group_value": 'Всего действительных голосов в группе: {s_votist}\\nВыберите дальнейшее действие',
        "back": '⬅️ Назад',
        "back_to_to_list_voting": 'Назад к списку голосований',
        "back_to_to_list_voting_1": 'Назад к списку голосований',
        "back_to_to_list_voting_2": 'Назад к списку голосований',
        "back_to_to_list_voting_3": 'Назад к списку голосований',
        "before": '➡️ Вперед',
        "choose_level_notification": 'Выберите уровень информирования.\\nМаксимальный: бот будет присылать все сообщения о создании голосований и их ходе.\nСредний: бот будет присылать сообщения о начале голосвания и его финальных этапах.\nМинимальный: вы не будете получать сообщений от бота о ходе голосований.\nПри любом уровне информирования вы будете получать важные сообщения от администрации и своего представителя',
        "choose_this_proxy": 'Выбрать этого представителя',
        "enter_unique_name_or_username": 'Введите уникальное имя или псевдоним.Это может быть ваше собственное имя (фамилия).Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей.И желательно не длиннее 40 символов',
        "error_empty_message_please_enter_username": 'Ошибка: пустое сообщение. Пожалуйста, введите псевдоним.',
        "f_description_proxy_info": ']}\\n" f"Описание:\\n{proxy_info[',
        "for_more_detailed_information_about_representative_info_pres": '\\nДля более подробной информации о представителе нажмите на соответствующую кнопку.',
        "in_present_time_no_active_voting": 'В настоящее время нет активных голосований.',
        "in_present_time_no_available_options": 'В настоящее время нет доступных вариантов.',
        "in_present_time_no_completed_voting": 'В настоящее время нет завершенных голосований.',
        "in_present_time_no_voting_in_stage_addition_options": 'В настоящее время нет голосований в стадии добавления вариантов.',
        "in_this_moment_no_available_representatives": 'В данный момент нет доступных представителей.',
        "incorrect_data": 'Некорректные данные.',
        "list_active_voting": 'Список активных голосований:',
        "list_completed_voting": 'Список завершенных голосований:',
        "list_future_voting": 'Список будущих голосований:',
        "list_options_to_golosovaniyu": 'Список вариантов к голосованию\\n',
        "list_representatives": '<b>Список представителей:</b>\\n\\n',
        "list_representatives_1": 'Список представителей',
        "main_menu": 'Главное меню',
        "main_menu_1": 'Главное меню',
        "occurred_error_data_not_found": 'Произошла ошибка. Данные не найдены.',
        "occurred_error_data_not_found_1": 'Произошла ошибка. Данные не найдены.',
        "occurred_error_message_not_found": 'Произошла ошибка. Сообщение не найдено.',
        "occurred_error_please_try_again": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_with_loading_list_representatives": 'Произошла ошибка при загрузке списка представителей.',
        "occurred_error_with_loading_list_voting": 'Произошла ошибка при загрузке списка голосований.',
        "occurred_error_with_saving_level_notification_try_later": 'Произошла ошибка при сохранении уровня информирования. Попробуйте позже.',
        "occurred_error_with_view_options_voting": 'Произошла ошибка при просмотре вариантов голосования.',
        "please_confirm_correct_is_entered_yours_name_username_value": 'Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?\n\n    {message_text}',
        "please_use_buttons": 'Пожалуйста, воспользуйтесь кнопками!\\n\\nЕсли вы хотите прервать изменение статуса - нажмите кнопку или отправьте команду /cancel',
        "please_use_buttons_above": 'Пожалуйста, воспользуйтесь кнопками выше!\\n\\nЕсли вы хотите прервать процедуру - нажмите кнопку под этим сообщением или отправьте команду /cancel',
        "return_in_main_menu": 'Вернуться в главное меню',
        "return_in_main_menu_1": 'Вернуться в главное меню',
        "return_in_main_menu_2": 'Вернуться в главное меню',
        "section_about_about_yourself_changed": 'Раздел "О себе" изменен!',
        "such_name_username_already_exists_try_invent_another_u": 'Такое имя/псевдоним уже есть. Попробуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас',
        "thank_you_username_not_changed_try_also_time_or_press_button": 'Спасибо! Псевдоним не изменен\\nПопробуйте еще раз, или нажмите кнопку для прерывания процедуры',
        "write_what_would_you_want_tell_about_about_yourself_drugim_u": 'Напишите, что бы вы хотели рассказать о себе другим участникам группы.\\nЕсли вы станете представителем - этот раздел смогут прочитать потенциальные подписчики\nЕсли хотите прервать процедуру - нажмите кнопку или наберите /cancel',
        "you_chosen_unknown_level": 'Вы выбрали: Неизвестный уровень',
        "you_chosen_value": 'Вы выбрали: {level_note}',
        "your_username_changed": 'Ваш псевдоним изменен!',
    },

    # ==BAN==
    "ban":{
        "user_banned_for_days":'''Вы забанены в группе до: "{ban_expiration}".\n
Вы по прежнему можете голосовать и доверять свой голос.\n
В случае несогласия с баном, пожалуйста, свяжитесь с администратором.''',
    },

    # ==CANDIDATE==

    "candidate": {
        "auth_success_you_member_group": 'Авторизация успешна! Вы участник группы.',
        "back": '⬅️ Назад',
        "back_1": '⬅️ Назад',
        "before": '➡️ Вперед',
        "before_1": '➡️ Вперед',
        "choose_interesting_info": 'Выберите интересующую информацию',
        "description": '\nОписание: ',
        "enter_unique_token_if_he_to_you_exists": 'Введите уникальный токен (если он у вас есть).\n',
        "error_in_data": 'Ошибка в данных.',
        "error_no_messages_for_edit": 'Ошибка: нет сообщения для редактирования.',
        "error_with_notification_super_registrator": 'Ошибка при уведомлении супер-регистратора: {result}',
        "error_with_notification_super_registrator_value": 'Ошибка при уведомлении супер-регистратора: {result}',
        "for_detailed_information_press_to_one_from_buttons_below": '\n\nДля подробной информации нажмите на одну из кнопок ниже:',
        "good_welcome_you_passed_by_special_link_this_bot_for_provede": '🎉 Добро пожаловать! Вы перешли по специальной ссылке.\nЭто бот для проведения голосований.\nПожалуйста, пройдите регистрацию, чтобы пользоваться ботом.\nТогда вы получите право голоса и возможность голосовать.\nДля более подробной информации, нажмите кнопку "Информация".',
        "here_should_was_be_info_about_bote": 'Здесь должна была быть информация о боте',
        "here_should_was_be_theory_about_newdem": 'Здесь должна была быть теория о ньюдеме',
        "in_this_moment_no_available_representatives": 'В данный момент нет доступных представителей.',
        "incorrect_data": 'Некорректные данные.',
        "list_representatives_username_number_votes": 'Список представителей: \n (Псевдоним, число голосов)',
        "list_representatives_username_number_votes_1": 'Список представителей: \n (Псевдоним, число голосов)',
        "main_menu": 'Главное меню',
        "main_menu_1": 'Главное меню',
        "not_found_info_about_representative_info": 'Не найдена информация о представителе',
        "not_found_profile_user": 'Не найден профиль пользователя',
        "not_success_determine_group": '❌ Не удалось определить группу.',
        "not_success_edit_message": 'Не удалось отредактировать сообщение.',
        "number_trusted_votes": 'Username: {username}\nОписание: {description}\nЧисло доверенных голосов: {trusted_votes}',
        "occurred_error": 'Произошла ошибка: {err}',
        "occurred_error_please_try_again": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_please_try_again_1": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_with_getting_information_about_representative": 'Произошла ошибка при получении информации о представителе.',
        "occurred_error_with_loading_list_representatives": 'Произошла ошибка при загрузке списка представителей.',
        "occurred_error_with_loading_list_voting": 'Произошла ошибка при загрузке списка голосований.',
        "occurred_error_with_loading_main_menu": 'Произошла ошибка при загрузке главного меню.',
        "please_use_buttons_if_you_want_cancel_change_status_send_com": 'Пожалуйста, воспользуйтесь кнопками!\n\nЕсли вы хотите прервать изменение статуса - отправьте команду /cancel',
        "prevysheno_quantity_attempts_input_token": 'Превышено количество попыток ввода токена.',
        "to_chto_you_entered_not_seems_to_token_try_again_or_type_can": 'То, что вы ввели не похоже на токен. Попробуйте снова или наберите /cancel.',
        "token_invalid_try_again_or_continue_questionnaire": 'Токен недействителен. Попробуйте снова или продолжите анкету.',
        "token_not_can_be_empty_try_eshch_time": 'Токен не может быть пустым. Попробуйте ещё раз:',
        "token_not_valid_try_again_or_continue_questionnaire": 'Токен не действителен. Попробуйте снова или продолжите анкету.',
        "you_consisting_in_group": 'Вы остались в группе',
        "you_exited_from_group": 'Вы вышли из группы!',
        "you_exited_from_machines_consisting_and_return_in_main_menu": 'Вы вышли из машины состояний и вернулись в главное меню.',
        "you_exited_in_main_menu": 'Вы вышли в главное меню.',
        "you_not_registered_in_group_proceed_registration": 'Вы не зарегистрированы в группе. Пройдите регистрацию',
        "you_returned_in_main_menu": 'Вы возвращены в главное меню.',
        "you_valid_want_exit_from_group_vs_correct": 'Вы действительно хотите выйти из группы?\nВсё верно?',
        "your_status_in_group": '\nВаш статус в группе:',
    },

    # ==DELEGATE==

    "delegate": {
        "error_value": 'Ошибка: {comment}',
        "error_value_1": 'Ошибка: {comment}',
        "occurred_error_please_try_again": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_value": 'Произошла ошибка: {err}',
        "occurred_error_value_1": 'Произошла ошибка: {err}',
        "option_not_created_want_is_add_another_option": 'Вариант не создан! Хотите ли добавить другой вариант?',
        "please_confirm_correct_is_entered_title_and_description_opti": 'Пожалуйста, подтвердите, правильно ли введены название и описание варианта?\n\nНазвание: {title}\nОписание: {description}',
        "please_confirm_correct_is_entered_title_and_description_voti": 'Пожалуйста, подтвердите, правильно ли введены название и описание голосования?\n\nНазвание: {title}\nОписание: {description}',
        "please_enter_description_option": 'Пожалуйста, введите описание варианта.',
        "please_enter_description_voting": 'Пожалуйста, введите описание голосования.',
        "please_enter_title_option": 'Пожалуйста, введите название варианта.',
        "please_enter_title_option_1": 'Пожалуйста, введите название варианта.',
        "please_enter_title_voting": 'Пожалуйста, введите название голосования.',
        "please_enter_title_voting_1": 'Пожалуйста, введите название голосования.',
        "thank_you_all_options_added_you_exited_from_machines_consist": 'Спасибо! Все варианты добавлены! Вы вышли из машины состояний.',
        "thank_you_option_created_nkhotite_is_add_eshch_option": 'Спасибо! Вариант создан!\\nХотите ли добавить ещё вариант?',
        "thank_you_voting_created_you_exited_from_machines_consisting": 'Спасибо! Голосование создано! Вы вышли из машины состояний.',
        "title_not_must_be_longer_40_characters_try_again": 'Название не должно быть длиннее 40 символов. Попробуйте снова.',
        "title_not_must_be_longer_40_characters_try_again_1": 'Название не должно быть длиннее 40 символов. Попробуйте снова.',
        "voting_not_created_try_also_time_you_exited_from_machines_co": 'Голосование не создано! Попробуйте еще раз. Вы вышли из машины состояний.',
    },

    # ==FROZEN==

    "frozen": {
        "auth_success_you_member_group": 'Авторизация успешна! Вы участник группы.',
        "enter_a_unique_token": 'Введите уникальный токен (если он у вас есть).\\n',
        "error notifying super registrar": 'Ошибка при уведомлении супер-регистратора: {result}',
        "error_with_notification_super_registrator": 'Ошибка при уведомлении супер-регистратора: ',
        "not_found_profile_user": 'Не найден профиль пользователя',
        "to_chto_you_entered_not_seems_to_token_try_again_or_type_can": 'То, что вы ввели не похоже на токен. Попробуйте снова или наберите /cancel.',
        "to_you_no_confirming_token_or_expired_period_his_actions_pop": 'У вас нет подтверждающего токена или истек срок его действия".\nПопросите у администрации новый токен.',
        "to_you_no_confirming_token_or_expired_period_his_actions_pop_1": 'У вас нет подтверждающего токена или истек срок его действия".\nПопросите у администрации новый токен.',
        "token cannot be empty": 'Токен не может быть пустым. Попробуйте ещё раз:',
        "token_invalid_try_again_or_continue_questionnaire": 'Токен недействителен. Попробуйте снова или продолжите анкету.',
        "token_not_valid_try_again_or_continue_questionnaire": 'Токен не действителен. Попробуйте снова или продолжите анкету.',
        "you_don't_have_verification_token": 'У вас нет подтверждающего токена или истек срок его действия.\nПопросите у администрации новый токен.',
        "you_not_registered_in_group_proydite_registratsiyu": 'Вы не зарегистрированы в группе. Пройдите регистрацию',
    },

    # ==LAST==
    "last": {
        "you_pressed_button_value_n": 'Вы нажали кнопку: "{butt_data}".\nОна не была обработанаЕсли вам нужна помощь, используйте команду /help.',
        "you_written_value_n": 'Вы написали: "{text}".\nВаше сообщение не было обработано\nЕсли вам нужна помощь, используйте команду /help.',
    },

    # ==MEMBER==
    "member": {
        "back": '⬅️ Назад',
        "back_1": '⬅️ Назад',
        "before": '➡️ Вперед',
        "before_1": '➡️ Вперед',
        "choose_proxy_kotoromu_you_trust_your_vote": 'Выберите представителя, которому вы доверите свой голос:',
        "detailed_info": 'Подробная информация',
        "detailed_info_1": 'Подробная информация',
        "enter_unique_name_or_username": 'Введите уникальное имя или псевдоним.Это может быть ваше собственное имя (фамилия).Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей.И желательно не длиннее 40 символов',
        "enter_unique_name_or_username_1": 'Введите уникальное имя или псевдоним.\\nЭто может быть ваше собственное имя (фамилия).\nВажно, чтобы оно было уникальным для этой группы,\nчтобы пользователи различали представителей.\nЖелательно не длиннее 40 символов.',
        "enter_unique_name_or_username_2": 'Введите уникальное имя или псевдоним.Это может быть ваше собственное имя (фамилия).Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей.И желательно не длиннее 40 символов',
        "enter_username": 'Введите псевдоним.',
        "enter_username_1": 'Введите псевдоним.',
        "error_in_data": 'Ошибка в данных.',
        "error_user_not_found": 'Ошибка: пользователь не найден',
        "error_with_voting_value": 'Ошибка при голосовании: {message}',
        "in_this_moment_no_available_representatives": 'В данный момент нет доступных представителей.',
        "in_this_moment_no_available_representatives_1": 'В данный момент нет доступных представителей.',
        "incorrect_data": 'Некорректные данные.',
        "main_menu": 'Главное меню',
        "main_menu_1": 'Главное меню',
        "not_found_info_about_representative_info": 'Не найдена информация о представителе',
        "not_found_profile_user": 'Не найден профиль пользователя',
        "occurred_error_please_try_again": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_please_try_again_1": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_please_try_again_2": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_please_try_again_3": 'Произошла ошибка. Пожалуйста, попробуйте снова.',
        "occurred_error_try_later": 'Произошла ошибка. Попробуйте позже.',
        "occurred_error_try_later_1": 'Произошла ошибка. Попробуйте позже.',
        "occurred_error_value": 'Произошла ошибка: {err}',
        "occurred_error_value_1": 'Произошла ошибка: {err}',
        "occurred_error_with_assignment_status_proxy": 'Произошла ошибка при присвоении статуса представителя.',
        "occurred_error_with_assignment_status_proxy_1": 'Произошла ошибка при присвоении статуса представителя.',
        "occurred_error_with_assignment_status_proxy_2": 'Произошла ошибка при присвоении статуса представителя.',
        "occurred_error_with_assignment_status_registrator": 'Произошла ошибка при присвоении статуса регистратора.',
        "occurred_error_with_choice_deputy": 'Произошла ошибка при выборе заместителя.',
        "occurred_error_with_deletion_status_admin": 'Произошла ошибка при удалении статуса администратора.',
        "occurred_error_with_deletion_status_proxy": 'Произошла ошибка при удалении статуса представителя.',
        "occurred_error_with_getting_information_about_representative": 'Произошла ошибка при получении информации о представителе.',
        "occurred_error_with_loading_list_representatives": 'Произошла ошибка при загрузке списка представителей.',
        "occurred_error_with_loading_list_representatives_1": 'Произошла ошибка при загрузке списка представителей.',
        "occurred_error_with_trust_votes": 'Произошла ошибка при доверии голоса.',
        "occurred_error_with_voting": 'Произошла ошибка при голосовании.',
        "offer_become_registrator_intended_not_you": 'Предложение стать регистратором предназначалось не вам',
        "offer_become_registrator_intended_not_you_1": 'Предложение стать регистратором предназначалось не вам',
        "please_confirm_correct_is_entered_yours_name_username_value": 'Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?\n\n{username}',
        "please_confirm_correct_is_entered_yours_name_username_value_1": 'Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?\n\n{username}',
        "please_enter_telegram_id_member_whose_you_want_to_do_yours_z": 'Пожалуйста, введите телеграм-ID участника,\n\n    которого вы хотите сделать своим заместителем или отправьте контакт с ID',
        "please_use_buttons": 'Пожалуйста, воспользуйтесь кнопками!\\n\\nЕсли вы хотите прервать изменение статуса - отправьте команду /cancel',
        "please_use_buttons_1": 'Пожалуйста, воспользуйтесь кнопками!\\n\\nЕсли вы хотите прервать процедуру - отправьте команду /cancel',
        "such_name_username_already_exists_try_invent_another_usernam": 'Такое имя/псевдоним уже есть. Попробуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас',
        "such_name_username_already_exists_try_invent_another_usernam_1": 'Такое имя/псевдоним уже есть. Попробуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас',
        "thank_you_username_not_added_try_also_time_or_press_button_f": 'Спасибо! Псевдоним не добавлен\\nПопробуйте еще раз, или нажмите кнопку для прерывания процедуры',
        "thank_you_username_not_added_try_enter_username_also_time_or": 'Спасибо! Псевдоним не добавлен\\nПопробуйте ввести псевдоним еще раз, или нажмите кнопку для прерывания процедуры',
        "unknown_error_with_assignment_deputy": 'Неизвестная ошибка при назначении заместителя.',
        "unknown_user": 'неизвестный пользователь',
        "unknown_user_1": 'неизвестный пользователь',
        "username_value_description_value_number_trusted_votes_value": 'Username: {username}\\nОписание: {description}\\nЧисло доверенных голосов: {trusted_votes}',
        "value_use_buttons_under_last_soobshcheniem_for_dalьneyshikh_": '{message}\\n\\nВоспользуйтесь кнопками под последним сообщением для дальнейших действий',
        "you_already_are_proxy": 'Вы уже являетесь представителем',
        "you_already_are_registrator": 'Вы уже являетесь регистратором',
        "you_already_are_registrator_1": 'Вы уже являетесь регистратором',
        "you_became_proxy": 'Вы стали представителем!',
        "you_became_proxy_1": 'Вы стали представителем!',
        "you_became_registrator": 'Вы стали регистратором!',
        "you_became_registrator_1": 'Вы стали регистратором!',
        "you_became_registrator_2": 'Вы стали регистратором!',
        "you_must_choose_about_yourself_proxy_to_have_right_vote": '\\nВам требуется выбрать себе представителя, чтобы иметь право голосовать',
        "you_not_are_candidate_in_registrators": 'Вы не являетесь кандидатом в регистраторы',
        "you_not_are_candidate_in_registrators_1": 'Вы не являетесь кандидатом в регистраторы',
        "you_not_are_candidate_in_registrators_2": 'Вы не являетесь кандидатом в регистраторы',
        "you_not_are_member_group": 'Вы не являетесь участником группы.',
        "you_not_are_member_group_1": 'Вы не являетесь участником группы.',
        "you_not_are_member_group_2": 'Вы не являетесь участником группы.',
        "you_not_are_member_group_3": 'Вы не являетесь участником группы.',
        "you_not_are_member_group_4": 'Вы не являетесь участником группы.',
        "you_not_are_member_group_5": 'Вы не являетесь участником группы.',
        "you_not_became_registrator": 'Вы не стали регистратором!',
        "you_resigned_ot_role_admin": 'Вы отказались от роли администратора!',
        "you_resigned_ot_role_registrator": 'Вы отказались от роли регистратора!',
        "you_stopped_be_proxy": 'Вы перестали быть представителем!',
    },

    # ==PROXY==
    "proxy": {
        "enter_text_rassylki": 'Введите текст рассылки:',
        "message_slishkom_dlinnoe_maks_4000_characters_try_again": 'Сообщение слишком длинное (макс. 4000 символов). попробуйте снова',
        "text_not_can_be_empty_try_eshch_time": 'Текст не может быть пустым. Попробуйте ещё раз:',
    },

    # ==REG_PROCESS==
    "reg_process": {
        "auth_success_you_member_group": 'Авторизация успешна! Вы участник группы.',
        "enter_text": 'Введите текст.',
        "enter_unique_token_if_he_to_you_exists": 'Введите уникальный токен (если он у вас есть).\\nЕсли нет — ответьте на вопросы администрации.\n\n',
        "error_not_found_info_about_group": 'Ошибка. Не найдена информация о группе',
        "error_with_notification_registrator_value": 'Ошибка при уведомлении регистратора: {result}',
        "error_with_notification_super_registrator_value": 'Ошибка при уведомлении супер-регистратора: {result}',
        "exceeded_quantity_attempts_input_token": 'Превышено количество попыток ввода токена.',
        "nobody_from_registratorov_not_know": 'Никого из регистраторов не знаю',
        "occurred_error_value": 'Произошла ошибка: {err}',
        "thank_you_choose_registrator": "Спасибо!\\nВыберите регистратора, которого знаете,\\nчтобы он мог подтвердить вашу личность.\\nЕсли никого не знаете — нажмите 'Никого не знаю'",
        "thank_you_yours_data_saved": 'Спасибо! Ваши данные сохранены.\\nАдминистрация их проверит и даст вам соответствующие права.\nВы вышли из машины состояний.',
        "token_invalid_try_again_or_continue_questionnaire": 'Токен недействителен. Попробуйте снова или продолжите анкету.',
        "token_not_valid_try_again_or_continue_questionnaire": 'Токен не действителен. Попробуйте снова или продолжите анкету.',
        "write_about_about_yourself": 'Напишите о себе',
        "you_already_registered_in_group": 'Вы уже зарегистрированы в группе.',
    },

    # ==REGISTRATOR==
    "registrator": {
        "comment_not_can_be_empty_try_once_more_time": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "comment_not_can_be_empty_try_once_more_time_1": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "congratulate_your_application_to_join_in_group_approved_or_y": 'Поздравляем! Ваша заявка на вступление в группу одобрена (либо ваши права участника восстановлены). Теперь вы полноправный участник группы и можете принимать участие в голосованиях.\\n\\nОбратите внимание - чтобы ваш голос учитывался, вам нужно либо выбрать себе представителя, либо сами стать представителем.\nВыбор представителя не ограничивает вашу возможность голосовать самому в любом голосовании.\nНо если вы не приняли участие в голосовании, будет учитываться то, как за вас проголосовал ваш представитель.\nЕсли вас не будет устраивать то, как за вас голосует ваш представитель, вы в любой момент сможете его поменять, либо сами стать представителем.\nСтатус представителя накладывает обязательства, например — участие во всех голосованиях.\nПредставитель может выбрать себе заместителя, который будет голосовать за него в случае отсутствия.\nПредставитель несёт ответственность за голосование своего заместителя, как за своё собственное.',
        "enter_comment_for_token": 'Введите комментарий для токена:',
        "error_with_binding_token_to_user_value": 'Ошибка при привязке токена к пользователю: {msg}',
        "internal_error_try_later": 'Внутренняя ошибка. Попробуйте позже.',
        "message_unavailable": 'Сообщение недоступно',
        "not_success_finish_registration": 'Не удалось завершить регистрацию.',
        "not_success_get_id_user_please_try_once_more_time": 'Не удалось получить ID пользователя. Пожалуйста, попробуйте ещё раз.',
        "occurred_error_with_confirmation_membership": 'Произошла ошибка при подтверждении членства.',
        "occurred_error_with_rejection_membership": 'Произошла ошибка при отклонении членства.',
        "received_inaccessiblemessage": 'Получено InaccessibleMessage',
        "thank_you_user_value_not_received_status_member": "Спасибо! Пользователь {tg_id} не получил статус 'Участник'.",
        "thank_you_user_value_received_status_member": "Спасибо! Пользователь {tg_id} получил статус 'Участник'.",
        "user_with_id_value_not_found": 'Пользователь с ID {tg_id} не найден.',
        "user_with_id_value_not_found_1": 'Пользователь с ID {tg_id} не найден.',
    },

    # ==SHORT_REG_PROCESS==
    "short_reg_process": {
        "error_not_found_info_about_group": 'Ошибка. Не найдена информация о группе',
        "error_with_notification_registrator_value": 'Ошибка при уведомлении регистратора: {result}',
        "error_with_notification_super_registrator_value": 'Ошибка при уведомлении супер-регистратора: {result}',
        "message_unavailable": 'Сообщение недоступно',
        "nobody_from_registrators_not_know": 'Никого из регистраторов не знаю',
        "occurred_error_value": 'Произошла ошибка: {str(e)}',
        "occurred_error_with_start_process_registration": 'Произошла ошибка при начале процесса регистрации.',
        "please_use_buttons_with_choice_moderator_if_you_want_cancel_": 'Пожалуйста, пользуйтесь кнопками при выборе модератора.\\n\\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel',
        "thank_you_choose_registrator_whose_know_to_he_could_confirm_": "Спасибо!\\nВыберите регистратора, которого знаете,\\nчтобы он смог подтвердить вашу личность\\nЕсли никого не знаете,\\nНажмите кнопку 'Никого не знаю'",
        "thank_you_yours_data_saved_admin_team_them_confirm_and_given": 'Спасибо! Ваши данные сохранены.\\nАдминистрация их проверит и даст вам соответствующие права\\nВы вышли из машины состояний',
        "write_about_about_yourself": 'Напишите о себе',
        "you_already_registered_in_group": 'Вы уже зарегистрированы в группе',
    },

    # ==TOKEN==
    "token": {
        "comment_not_can_be_empty_try_once_more_time": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "comment_not_can_be_empty_try_once_more_time_1": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "comment_not_can_be_empty_try_once_more_time_2": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "comment_not_can_be_empty_try_once_more_time_3": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "comment_not_can_be_empty_try_once_more_time_4": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "comment_not_can_be_empty_try_once_more_time_5": 'Комментарий не может быть пустым. Попробуйте ещё раз:',
        "created_tokeny_lot_value_value": "Созданы токены лота №",
        "enter_comment_for_these_tokens": 'Введите комментарий для этих токенов:',
        "enter_comment_for_these_tokens_1": 'Введите комментарий для этих токенов:',
        "enter_comment_for_this_token": 'Введите комментарий для этого токена:',
        "enter_correct_number": 'Введите корректное число.',
        "enter_correct_number_1": 'Введите корректное число.',
        "enter_correct_token": 'Введите корректный токен.',
        "enter_correct_token_1": 'Введите корректный токен.',
        "enter_number_existing_lot_or_press_button_below_if_lot_new": 'Введите номер существующего лота или нажмите кнопку ниже, если лот новый:',
        "enter_token_for_mark_kak_obsolete": 'Введите токен для пометки как устаревший:',
        "export_tokens": 'Экспорт токенов',
        "how_much_tokens_create": 'Сколько токенов создать?',
        "how_much_tokens_create_1": 'Сколько токенов создать?',
        "how_much_tokens_issue": 'Сколько токенов выдать?',
        "issued_token_value": 'Выдан токен:\\n\\n<code>{tokens_list}</code>',
        "issued_tokeny_value": 'Выданы токены:\\n{tokens_list}',
        "menu_management_tokens": 'Меню управления токенами:',
        "menu_management_tokens_1": 'Меню управления токенами:',
        "menu_management_tokens_2": 'Меню управления токенами:',
        "menu_management_tokens_3": 'Меню управления токенами:',
        "not_specified_quantity_tokens": '❌ Не указано количество токенов.',
        "not_success_create_lot_tokens": 'Не удалось создать лот токенов.',
        "not_success_export_tokeny": 'Не удалось экспортировать токены.',
        "not_success_issue_tokeny": 'Не удалось выдать токены.',
        "not_success_issue_tokeny_1": 'Не удалось выдать токены.',
        "not_success_update_status_token": 'Не удалось обновить статус токена.',
        "number_lot_must_be_chislom_try_once_more_time": 'Номер лота должен быть числом. Попробуйте ещё раз:',
        "return_in_main_menu": 'Возврат в главное меню:',
        "skip_avtomaticheskiy_number": 'Пропустить (автоматический номер)',
        "token_not_found_or_already_expired": 'Токен не найден или уже устарел.',
        "token_success_marked_kak_obsolete": 'Токен успешно помечен как устаревший.',
    },
}
