from aiogram.fsm.state import StatesGroup, State

class CreateAdStates(StatesGroup):
    selecting_channel = State()
    content = State()
    scheduled_time = State()
    duration = State()

class AddChannelStates(StatesGroup):
    waiting_for_channel = State()