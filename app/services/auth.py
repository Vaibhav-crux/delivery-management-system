from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from models.user import User, UserStatus
from core.jwt import JWTConfig
from sqlalchemy import select
import logging
import traceback
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, session_factory, jwt_config: JWTConfig):
        self.session_factory = session_factory
        self.jwt_config = jwt_config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def signup(self, username: str, email: str, password: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Check if user already exists
                existing_user = await session.execute(
                    select(User).where((User.username == username) | (User.email == email))
                )
                user = existing_user.scalars().first()
                if user:
                    if user.status == UserStatus.INACTIVE:
                        # Update inactive user to PENDING
                        user.hashed_password = self.pwd_context.hash(password)
                        user.status = UserStatus.PENDING
                        user.is_active = False
                        await session.commit()
                        await session.refresh(user)
                        logger.info(f"Inactive user reactivated to PENDING: {username}")
                    else:
                        logger.warning(f"Signup attempt with existing username/email: {username}/{email}")
                        return {"error": "Username or email already exists"}

                else:
                    # Create new user with PENDING status
                    hashed_password = self.pwd_context.hash(password)
                    user = User(
                        username=username,
                        email=email,
                        hashed_password=hashed_password,
                        is_active=False,
                        status=UserStatus.PENDING
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)

                # Generate JWT token
                token = self.jwt_config.create_access_token({"sub": str(user.id)})
                logger.info(f"User signed up successfully: {username}")
                return {"token": token, "user_id": str(user.id)}
            except Exception as e:
                await session.rollback()
                logger.error(f"Signup failed for {username}: {str(e)}", exc_info=True)
                return {"error": f"Failed to create user: {str(e)}"}

    async def login(self, username: str, password: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Find user
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalars().first()
                if not user:
                    logger.warning(f"Login attempt with non-existent username: {username}")
                    return {"error": "Invalid credentials"}

                # Verify password
                if not self.pwd_context.verify(password, user.hashed_password):
                    logger.warning(f"Invalid password attempt for username: {username}")
                    return {"error": "Invalid credentials"}

                # Check if user is inactive
                if user.status == UserStatus.INACTIVE:
                    logger.warning(f"Login attempt for inactive user: {username}")
                    return {"error": "Account is inactive. Please sign up again."}

                # Update status to ACTIVE if PENDING
                if user.status == UserStatus.PENDING:
                    user.status = UserStatus.ACTIVE
                    user.is_active = True
                    await session.commit()
                    await session.refresh(user)
                    logger.info(f"User status updated to ACTIVE: {username}")

                # Generate JWT token
                token = self.jwt_config.create_access_token({"sub": str(user.id)})
                logger.info(f"User logged in successfully: {username}")
                return {"token": token, "user_id": str(user.id)}
            except Exception as e:
                logger.error(f"Login failed for {username}: {str(e)}", exc_info=True)
                return {"error": f"Login failed: {str(e)}"}

    async def delete_user(self, user_id: str, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Verify JWT token
                payload = jwt.decode(
                    token,
                    self.jwt_config.secret_key,
                    algorithms=[self.jwt_config.algorithm]
                )
                token_user_id = payload.get("sub")
                if token_user_id != user_id:
                    logger.warning(f"Unauthorized delete attempt for user_id: {user_id}")
                    return {"error": "Unauthorized", "status": 401}

                # Find user
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalars().first()
                if not user:
                    logger.warning(f"Delete attempt for non-existent user_id: {user_id}")
                    return {"error": "User not found", "status": 404}

                # Set status to INACTIVE
                user.status = UserStatus.INACTIVE
                user.is_active = False
                await session.commit()
                logger.info(f"User set to INACTIVE: {user_id}")
                return {"message": "User account deactivated"}
            except JWTError as e:
                logger.warning(f"Invalid JWT token for delete user: {str(e)}")
                return {"error": "Invalid token", "status": 401}
            except Exception as e:
                await session.rollback()
                logger.error(f"Delete user failed for {user_id}: {str(e)}", exc_info=True)
                return {"error": f"Failed to deactivate user: {str(e)}", "status": 500}

    async def validate_user_token(self, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Verify JWT token
                payload = jwt.decode(
                    token,
                    self.jwt_config.secret_key,
                    algorithms=[self.jwt_config.algorithm]
                )
                user_id = payload.get("sub")
                if not user_id:
                    logger.warning("Invalid token: no user_id in payload")
                    return {"error": "Invalid token", "status": 401}

                # Find user
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalars().first()
                if not user:
                    logger.warning(f"Token validation failed: user_id {user_id} not found")
                    return {"error": "User not found", "status": 404}

                # Check if user is inactive
                if user.status == UserStatus.INACTIVE:
                    logger.warning(f"Token validation failed: user_id {user_id} is inactive")
                    return {"error": "Account is inactive", "status": 403}

                return {"user_id": user_id, "status": 200}
            except JWTError as e:
                logger.warning(f"Invalid JWT token: {str(e)}")
                return {"error": "Invalid token", "status": 401}
            except Exception as e:
                logger.error(f"Token validation failed: {str(e)}", exc_info=True)
                return {"error": f"Token validation failed: {str(e)}", "status": 500}