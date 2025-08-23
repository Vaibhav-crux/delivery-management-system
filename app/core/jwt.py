from datetime import datetime, timedelta
from jose import JWTError, jwt
from config.settings import Config

class JWTConfig:
    def __init__(self, config: Config):
        self.secret_key = config.SECRET_KEY
        self.algorithm = config.JWT_ALGORITHM
        self.expiration_time = config.JWT_EXPIRATION_TIME

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(seconds=self.expiration_time)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None