from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    # Example state
    waiting_for_vpn_key = State()
    # Промокод
    waiting_for_promocode = State()

class RenameKey(StatesGroup):
    waiting_for_name = State()

class ReplaceKey(StatesGroup):
    users_server = State()
    users_inbound = State()
    confirm = State()

class NewKeyConfig(StatesGroup):
    waiting_for_server = State()
    waiting_for_inbound = State()
