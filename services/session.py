
class AdminSession:
    def __init__(self):
        self.active_admins = set()

    def login(self, user_id: int):
        self.active_admins.add(user_id)

    def logout(self, user_id: int):
        self.active_admins.discard(user_id)

    def is_active(self, user_id: int) -> bool:
        return user_id in self.active_admins

admin_session = AdminSession()