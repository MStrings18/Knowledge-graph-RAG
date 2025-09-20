import { createBrowserRouter} from 'react-router-dom'
import Login from './../Pages/Login';
import Signup from './../Pages/Signup';
import Chatbot from '../Pages/chatbot';


const userRouter = createBrowserRouter(
  [
    {
      path:"/",
      element:
        <div>
            <Login/>
        </div>,
    },
    {
      path:"/signup",
      element:
        <div>
            <Signup/>
        </div>,
    },
    {
      path:"/chatbot",
      element:
        <div>
            <Chatbot/>
        </div>,
    },
    
  ]
)

export default userRouter