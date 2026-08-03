class TraineeModel:
    def __init__(self, full_name="", trainee_id=""):
        self.full_name = full_name
        self.trainee_id = trainee_id

    def to_dict(self):
        return {
            "full_name": self.full_name,
            "trainee_id": self.trainee_id,
        }
